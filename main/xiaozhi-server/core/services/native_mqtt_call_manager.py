import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from config.logger import setup_logging

logger = setup_logging()


def normalize_device_id(device_id: Optional[str]) -> Optional[str]:
    if not isinstance(device_id, str):
        return None
    normalized = device_id.strip().lower().replace("-", ":")
    return normalized or None


@dataclass(frozen=True)
class PendingCall:
    caller_mac: str
    target_mac: str
    caller_nickname: str
    created_at: float
    generation: int


class NativeMqttCallManager:
    def __init__(
        self,
        connection_registry,
        timeout_seconds: float = 60,
        silence_frame: Optional[bytes] = None,
        clock=time.monotonic,
    ):
        self.connection_registry = connection_registry
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.silence_frame = silence_frame
        self.clock = clock
        self.pending_calls: Dict[str, PendingCall] = {}
        self.active_calls: Dict[str, str] = {}
        self.call_session_ids: Dict[str, str] = {}
        self.call_generations: Dict[str, int] = {}
        self._next_generation = 1
        self._generation_end_events: Dict[int, asyncio.Event] = {}
        self._end_tasks: Dict[tuple[str, int], asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def request_call(
        self,
        caller_mac: str,
        target_mac: str,
        caller_nickname: str = "",
    ) -> Dict[str, Any]:
        caller = normalize_device_id(caller_mac)
        target = normalize_device_id(target_mac)
        if not caller or not target or caller == target:
            return {"status": "error", "message": "呼叫设备参数无效"}

        caller_entry = self.connection_registry.resolve_device_now(caller)
        target_entry = self.connection_registry.resolve_device_now(target)
        if target_entry is None:
            return {"status": "offline", "message": "对方设备不在线，请稍后重试"}
        if caller_entry is None:
            return {"status": "error", "message": "主叫设备不在线"}

        async with self._lock:
            if caller in self.active_calls or target in self.active_calls:
                return {"status": "error", "message": "设备已在通话中"}
            caller_pending = self._pending_owner_locked(caller)
            target_pending = self._pending_owner_locked(target)
            reverse = (
                caller_pending == target
                and target_pending == target
                and self.pending_calls[target].target_mac == caller
            )
            if reverse:
                pending = self.pending_calls.pop(target)
                self.active_calls[caller] = target
                self.active_calls[target] = caller
                generation = pending.generation
                status = "bridged"
            elif caller_pending or target_pending:
                return {"status": "error", "message": "设备已有等待中的通话"}
            else:
                generation = self._allocate_generation_locked()
                self.pending_calls[caller] = PendingCall(
                    caller_mac=caller,
                    target_mac=target,
                    caller_nickname=caller_nickname or "",
                    created_at=self.clock(),
                    generation=generation,
                )
                status = "pending"
            self.call_generations[caller] = generation
            self.call_generations[target] = generation
            self._capture_session(caller, caller_entry)
            self._capture_session(target, target_entry)
            self._set_call_state(caller_entry, True)
            if status == "bridged":
                self._set_call_state(target_entry, True)

        try:
            await self._stop_ai_session(
                caller_entry, self.call_session_ids.get(caller)
            )
            if status == "bridged":
                await self._stop_ai_session(
                    target_entry, self.call_session_ids.get(target)
                )
        except asyncio.CancelledError:
            await self.end_call(
                caller,
                notify_device=False,
                notify_peer=False,
                expected_generation=generation,
            )
            raise
        except Exception as error:
            await self.end_call(
                caller,
                notify_device=True,
                notify_peer=status == "bridged",
                expected_generation=generation,
            )
            logger.warning(
                "Native MQTT停止AI会话失败: caller={}, target={}, error={}",
                caller,
                target,
                error,
            )
            return {"status": "error", "message": "停止AI会话失败"}

        async with self._lock:
            if status == "pending":
                valid = self._pending_matches_locked(
                    caller, target, generation
                )
            else:
                valid = self._active_matches_locked(
                    caller, target, generation
                )
        if not valid:
            return {"status": "error", "message": "通话状态已变化"}

        if status == "pending":
            try:
                sent = await self._send_while_generation_active(
                    target_entry.transport,
                    {
                        "type": "mcp",
                        "payload": {
                            "jsonrpc": "2.0",
                            "id": 9999,
                            "method": "tools/call",
                            "params": {
                                "name": "self.remote_wakeup",
                                "arguments": {
                                    "reason": (
                                        "[device_call]您收到来自"
                                        f"{caller_nickname or '未知'}的来电，是否接听？"
                                    ),
                                    "action": "listen",
                                },
                            },
                        },
                    },
                    generation,
                )
                if not sent:
                    return {"status": "error", "message": "通话状态已变化"}
            except asyncio.CancelledError:
                await self.end_call(
                    caller,
                    notify_device=False,
                    notify_peer=False,
                    expected_generation=generation,
                )
                raise
            except Exception as error:
                await self.end_call(
                    caller,
                    "发送来电通知失败",
                    notify_device=True,
                    notify_peer=False,
                    expected_generation=generation,
                )
                logger.warning(
                    "Native MQTT来电通知发送失败: caller={}, target={}, error={}",
                    caller,
                    target,
                    error,
                )
                return {"status": "error", "message": "发送来电通知失败"}
        return {"status": status}

    async def accept_call(self, callee_mac: str) -> Dict[str, Any]:
        callee = normalize_device_id(callee_mac)
        if not callee:
            return {"status": "error", "message": "接听设备参数无效"}

        callee_entry = self.connection_registry.resolve_device_now(callee)
        if callee_entry is None:
            return {"status": "offline", "message": "接听设备不在线"}

        async with self._lock:
            if callee in self.active_calls:
                return {"status": "error", "message": "设备已在通话中"}
            pending = next(
                (
                    entry
                    for entry in self.pending_calls.values()
                    if entry.target_mac == callee
                ),
                None,
            )
            if pending is None:
                return {"status": "no_pending", "message": "没有等待中的通话"}

            caller = pending.caller_mac
            caller_entry = self.connection_registry.resolve_device_now(caller)
            if caller_entry is None:
                self._remove_call_locked(caller)
                self._set_call_state(callee_entry, False)
                return {
                    "status": "caller_gone",
                    "message": "主叫方已离开或通话已超时",
                }

            self.pending_calls.pop(caller, None)
            self.active_calls[caller] = callee
            self.active_calls[callee] = caller
            generation = pending.generation
            self.call_generations[caller] = generation
            self.call_generations[callee] = generation
            self._capture_session(caller, caller_entry)
            self._capture_session(callee, callee_entry)
            self._set_call_state(caller_entry, True)
            self._set_call_state(callee_entry, True)

        try:
            await self._stop_ai_session(
                callee_entry, self.call_session_ids.get(callee)
            )
        except asyncio.CancelledError:
            await self.end_call(
                callee,
                notify_device=False,
                notify_peer=False,
                expected_generation=generation,
            )
            raise
        except Exception as error:
            await self.end_call(
                callee,
                notify_device=True,
                notify_peer=True,
                expected_generation=generation,
            )
            logger.warning(
                "Native MQTT停止接听方AI会话失败: caller={}, callee={}, error={}",
                caller,
                callee,
                error,
            )
            return {"status": "error", "message": "停止AI会话失败"}

        async with self._lock:
            valid = self._active_matches_locked(
                caller, callee, generation
            )
        if not valid:
            return {"status": "error", "message": "通话状态已变化"}

        try:
            sent = await self._send_while_generation_active(
                caller_entry.transport,
                {"type": "call_accepted", "from": callee},
                generation,
            )
            if not sent:
                return {"status": "error", "message": "通话状态已变化"}
        except asyncio.CancelledError:
            await self.end_call(
                callee,
                notify_device=False,
                notify_peer=False,
                expected_generation=generation,
            )
            raise
        except Exception as error:
            await self.end_call(
                callee,
                "发送接听确认失败",
                notify_device=True,
                notify_peer=True,
                expected_generation=generation,
            )
            logger.warning(
                "Native MQTT接听确认发送失败: caller={}, callee={}, error={}",
                caller,
                callee,
                error,
            )
            return {"status": "error", "message": "发送接听确认失败"}
        return {"status": "bridged", "peerMac": caller}

    def route_audio(
        self, source_device_id: str, payload: bytes, timestamp: int
    ) -> bool:
        source = normalize_device_id(source_device_id)
        if not source:
            return False

        peer = self.active_calls.get(source)
        if peer:
            target = self.connection_registry.resolve_device_now(peer)
            if target is None:
                self._schedule_end(source, "对方已离开")
                return True
            handler = getattr(target.transport, "_udp_handler", None)
            try:
                sent = (
                    handler is not None
                    and handler.send_audio_nowait(payload, 0)
                )
            except Exception:
                sent = False
            if not sent:
                self._schedule_end(source, "对方音频通道不可用")
            return True

        if source in self.pending_calls:
            source_entry = self.connection_registry.resolve_device_now(source)
            handler = (
                getattr(source_entry.transport, "_udp_handler", None)
                if source_entry
                else None
            )
            if handler is not None and self.silence_frame:
                try:
                    handler.send_audio_nowait(self.silence_frame, 0)
                except Exception:
                    self._schedule_end(source, "主叫音频通道不可用")
            return True
        return False

    async def end_call(
        self,
        device_id: str,
        reason: str = "",
        notify_device: bool = False,
        notify_peer: bool = True,
        expected_session_id: Optional[str] = None,
        expected_generation: Optional[int] = None,
    ) -> bool:
        device = normalize_device_id(device_id)
        if not device:
            return False

        observed_generation = self.call_generations.get(device)
        generation = (
            expected_generation
            if expected_generation is not None
            else observed_generation
        )
        if observed_generation is None or observed_generation != generation:
            return False
        if (
            expected_session_id is not None
            and self.call_session_ids.get(device) != expected_session_id
        ):
            return False
        end_event = self._generation_end_events.get(generation)
        if end_event is not None:
            end_event.set()

        async with self._lock:
            current_generation = self.call_generations.get(device)
            if current_generation != generation:
                return False
            if expected_session_id is not None:
                current_session_id = self.call_session_ids.get(device)
                if current_session_id != expected_session_id:
                    return False
            related = self._remove_call_locked(device)
        if related is None:
            return False

        peer = related.get("peer")
        device_session = related.get("device_session")
        peer_session = related.get("peer_session")
        device_entry = self.connection_registry.resolve_device_now(device)
        peer_entry = (
            self.connection_registry.resolve_device_now(peer) if peer else None
        )
        self._set_call_state(device_entry, False)
        self._set_call_state(peer_entry, False)

        notifications = []
        if notify_device and device_entry is not None:
            notifications.append(
                self._notify_idle(device_entry, device_session, reason)
            )
        if notify_peer and peer_entry is not None:
            notifications.append(
                self._notify_idle(peer_entry, peer_session, reason)
            )
        if notifications:
            results = await asyncio.gather(
                *notifications, return_exceptions=True
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(
                        "Native MQTT通话结束通知失败: error={}", result
                    )
        return True

    async def cleanup_timeouts(self) -> int:
        expired = []
        now = self.clock()
        async with self._lock:
            for caller, pending in list(self.pending_calls.items()):
                if now - pending.created_at >= self.timeout_seconds:
                    expired.append((caller, pending.generation))
        for caller, generation in expired:
            await self.end_call(
                caller,
                "呼叫等待超时",
                notify_device=True,
                notify_peer=False,
                expected_generation=generation,
            )
        return len(expired)

    async def clear(self) -> None:
        tasks = list(self._end_tasks.values())
        self._end_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        async with self._lock:
            devices = set(self.pending_calls)
            devices.update(self.active_calls)
            devices.update(self.call_generations)
        for device in devices:
            await self.end_call(
                device,
                "服务停止",
                notify_device=False,
                notify_peer=False,
            )
        async with self._lock:
            remaining = set(self.call_generations)
            remaining.update(self.call_session_ids)
            self.pending_calls.clear()
            self.active_calls.clear()
            self.call_generations.clear()
            self.call_session_ids.clear()
            end_events = list(self._generation_end_events.values())
            self._generation_end_events.clear()
        for end_event in end_events:
            end_event.set()
        for device in remaining:
            self._set_call_state(
                self.connection_registry.resolve_device_now(device),
                False,
            )

    def contains(self, device_id: str) -> bool:
        device = normalize_device_id(device_id)
        return bool(
            device
            and (
                self._pending_owner_now(device) is not None
                or device in self.active_calls
            )
        )

    @property
    def count(self) -> int:
        devices = set(self.call_generations)
        devices.update(self.call_session_ids)
        devices.update(self.active_calls)
        devices.update(self.pending_calls)
        devices.update(
            pending.target_mac for pending in self.pending_calls.values()
        )
        generations = set(self.call_generations.values())
        orphan_events = set(self._generation_end_events) - generations
        return len(devices) + len(orphan_events)

    @property
    def background_task_count(self) -> int:
        return sum(not task.done() for task in self._end_tasks.values())

    async def handle_logical_hello(
        self, device_id: str, session_id: Optional[str]
    ) -> bool:
        device = normalize_device_id(device_id)
        if not device:
            return False
        async with self._lock:
            pending_owner = self._pending_owner_locked(device)
            if (
                pending_owner is not None
                and pending_owner != device
                and device not in self.active_calls
            ):
                if session_id:
                    self.call_session_ids[device] = session_id
                return False
            generation = self.call_generations.get(device)
        if generation is None:
            return False
        return await self.end_call(
            device,
            "设备重新进入AI会话",
            notify_device=False,
            notify_peer=True,
            expected_session_id=session_id,
            expected_generation=generation,
        )

    def _capture_session(self, device_id: str, entry) -> None:
        session_id = getattr(entry.transport, "session_id", None)
        if session_id:
            self.call_session_ids[device_id] = session_id

    def _drop_session(self, device_id: str) -> Optional[str]:
        return self.call_session_ids.pop(device_id, None)

    def _remove_call_locked(self, device: str) -> Optional[Dict[str, Any]]:
        generation = self.call_generations.get(device)
        end_event = self._generation_end_events.get(generation)
        if end_event is not None:
            end_event.set()
        pending = self.pending_calls.pop(device, None)
        if pending:
            self._drop_generation(device)
            self._drop_generation(pending.target_mac)
            self._generation_end_events.pop(pending.generation, None)
            return {
                "peer": pending.target_mac,
                "device_session": self._drop_session(device),
                "peer_session": self._drop_session(pending.target_mac),
            }

        pending_owner = next(
            (
                caller
                for caller, entry in self.pending_calls.items()
                if entry.target_mac == device
            ),
            None,
        )
        if pending_owner:
            pending = self.pending_calls.pop(pending_owner)
            self._drop_generation(device)
            self._drop_generation(pending_owner)
            self._generation_end_events.pop(pending.generation, None)
            return {
                "peer": pending_owner,
                "device_session": self._drop_session(device),
                "peer_session": self._drop_session(pending_owner),
            }

        peer = self.active_calls.pop(device, None)
        if peer:
            self.active_calls.pop(peer, None)
            self._drop_generation(device)
            self._drop_generation(peer)
            if generation is not None:
                self._generation_end_events.pop(generation, None)
            return {
                "peer": peer,
                "device_session": self._drop_session(device),
                "peer_session": self._drop_session(peer),
            }
        return None

    def _schedule_end(self, device_id: str, reason: str) -> None:
        device = normalize_device_id(device_id)
        generation = self.call_generations.get(device) if device else None
        if not device or generation is None:
            return
        key = (device, generation)
        existing = self._end_tasks.get(key)
        if existing is not None and not existing.done():
            return
        task = asyncio.create_task(
            self.end_call(
                device,
                reason,
                notify_device=True,
                notify_peer=True,
                expected_generation=generation,
            )
        )
        self._end_tasks[key] = task
        task.add_done_callback(
            lambda completed, task_key=key: self._discard_end_task(
                task_key, completed
            )
        )

    def _discard_end_task(
        self, key: tuple[str, int], task: asyncio.Task
    ) -> None:
        if self._end_tasks.get(key) is task:
            self._end_tasks.pop(key, None)
        if not task.cancelled():
            task.exception()

    def _allocate_generation_locked(self) -> int:
        generation = self._next_generation
        self._next_generation += 1
        self._generation_end_events[generation] = asyncio.Event()
        return generation

    async def _send_while_generation_active(
        self, transport, message: Dict[str, Any], generation: int
    ) -> bool:
        end_event = self._generation_end_events.get(generation)
        if end_event is None or end_event.is_set():
            return False
        send_task = asyncio.create_task(transport.send_json(message))
        end_task = asyncio.create_task(end_event.wait())
        try:
            done, _ = await asyncio.wait(
                {send_task, end_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if end_task in done:
                send_task.cancel()
                await asyncio.gather(send_task, return_exceptions=True)
                return False
            await send_task
            return not end_event.is_set()
        finally:
            if not send_task.done():
                send_task.cancel()
            if not end_task.done():
                end_task.cancel()
            await asyncio.gather(
                send_task, end_task, return_exceptions=True
            )

    def _pending_owner_locked(self, device: str) -> Optional[str]:
        if device in self.pending_calls:
            return device
        return next(
            (
                caller
                for caller, pending in self.pending_calls.items()
                if pending.target_mac == device
            ),
            None,
        )

    def _pending_owner_now(self, device: str) -> Optional[str]:
        return self._pending_owner_locked(device)

    def _pending_matches_locked(
        self, caller: str, target: str, generation: int
    ) -> bool:
        pending = self.pending_calls.get(caller)
        return bool(
            pending
            and pending.target_mac == target
            and pending.generation == generation
            and self.call_generations.get(caller) == generation
            and self.call_generations.get(target) == generation
        )

    def _active_matches_locked(
        self, caller: str, target: str, generation: int
    ) -> bool:
        return (
            self.active_calls.get(caller) == target
            and self.active_calls.get(target) == caller
            and self.call_generations.get(caller) == generation
            and self.call_generations.get(target) == generation
        )

    def _drop_generation(self, device_id: str) -> Optional[int]:
        return self.call_generations.pop(device_id, None)

    @staticmethod
    async def _stop_ai_session(entry, session_id: Optional[str]) -> None:
        if entry is None:
            return
        end_conversation = getattr(entry.context, "end_conversation", None)
        if callable(end_conversation):
            await end_conversation(session_id)
            return
        cancel_tasks = getattr(entry.context, "cancel_conversation_tasks", None)
        if callable(cancel_tasks):
            await cancel_tasks()

    @staticmethod
    def _set_call_state(entry, active: bool) -> None:
        if entry is None:
            return
        entry.context.calling = active
        if not active:
            entry.context.incoming_call = None

    @staticmethod
    async def _notify_idle(entry, session_id: Optional[str], reason: str) -> None:
        raw_connection = getattr(entry.transport, "raw_connection", None)
        if raw_connection is None:
            return
        try:
            await raw_connection.notify_device_idle(session_id)
        finally:
            end_conversation = getattr(entry.context, "end_conversation", None)
            if callable(end_conversation):
                await end_conversation(session_id)
        if reason:
            logger.info(
                "Native MQTT通话结束: device_id={}, reason={}",
                entry.context.device_id,
                reason,
            )
