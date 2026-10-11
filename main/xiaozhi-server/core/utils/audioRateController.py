import time
import asyncio
from collections import deque
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class AudioRateController:
    """
    Audio rate controller.
    Sends audio on a 60 ms frame cadence to avoid timing drift under load.
    """

    def __init__(self, frame_duration=60, send_delay=0):
        """
        Args:
            frame_duration: Duration of each audio frame in milliseconds.
        """
        # Flow control interval (ms): use config value if send_delay > 0, otherwise use frame_duration
        self.interval_ms = send_delay if send_delay > 0 else frame_duration
        self.queue = deque()
        self.play_position = 0  # Virtual playback position in milliseconds.
        self.start_timestamp = None  # Start timestamp, set once per send cycle.
        self.pending_send_task = None
        self.logger = logger
        self.queue_empty_event = asyncio.Event()  # Signals an empty queue.
        self.queue_empty_event.set()  # Queue starts empty.
        self.queue_has_data_event = asyncio.Event()  # Signals pending queue data.
        self._last_queue_empty_time = 0  # Last time the queue became empty.

    def reset(self):
        """Reset controller state."""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            # The task will clean itself up on the next event-loop tick.

        self.queue.clear()
        self.play_position = 0
        self.start_timestamp = None  # Set by the first outgoing audio packet.
        self._last_queue_empty_time = 0
        # Reset queue state events.
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()

    def add_audio(self, opus_packet):
        """Add an audio packet to the queue."""
        # If the queue was empty, adjust timestamps so resumed playback stays
        # aligned and new audio does not jump ahead unexpectedly.
        if len(self.queue) == 0 and self.play_position > 0:
            elapsed_since_empty = (time.monotonic() - self._last_queue_empty_time) * 1000
            # Treat gaps longer than one frame as a real pause/resume cycle.
            if elapsed_since_empty >= self.frame_duration:
                self.start_timestamp = time.monotonic() - (self.play_position / 1000)
                self.logger.bind(tag=TAG).debug(
                    f"Queue resumed from empty state; reset timestamp. Playback position: {self.play_position}ms, gap: {elapsed_since_empty:.0f}ms"
                )

        self.queue.append(("audio", opus_packet))
        # Update queue state events.
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def add_message(self, message_callback):
        """
        Add a message callback to the queue.

        Args:
            message_callback: Async callback used to send the message.
        """
        if len(self.queue) == 0 and self.play_position > 0:
            elapsed_since_empty = (time.monotonic() - self._last_queue_empty_time) * 1000
            if elapsed_since_empty >= self.interval_ms:
                self.start_timestamp = time.monotonic() - (self.play_position / 1000)
                self.logger.bind(tag=TAG).debug(
                    f"Queue resumed from empty state; reset timestamp. Playback position: {self.play_position}ms, gap: {elapsed_since_empty:.0f}ms"
                )

        self.queue.append(("message", message_callback))
        # Update queue state events.
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def _get_elapsed_ms(self):
        """Get the elapsed playback time in milliseconds."""
        if self.start_timestamp is None:
            return 0
        return (time.monotonic() - self.start_timestamp) * 1000

    async def check_queue(self, send_audio_callback):
        """
        Check the queue and send audio or messages on schedule.

        Args:
            send_audio_callback: Async callback used to send audio packets.
        """
        while self.queue:
            item = self.queue[0]
            item_type = item[0]

            if item_type == "message":
                # Message items are sent immediately and do not consume playback time.
                _, message_callback = item
                self.queue.popleft()
                try:
                    await message_callback()
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to send message: {e}")
                    raise

            elif item_type == "audio":
                if self.start_timestamp is None:
                    self.start_timestamp = time.monotonic()

                _, opus_packet = item

                # Wait until it is time to send the next audio packet.
                while True:
                    # Compute the remaining wait time.
                    elapsed_ms = self._get_elapsed_ms()
                    output_ms = self.play_position

                    if elapsed_ms < output_ms:
                        # It is not time yet, so wait for the remaining delay.
                        wait_ms = output_ms - elapsed_ms

                        # Sleep, allowing cancellation.
                        try:
                            await asyncio.sleep(wait_ms / 1000)
                        except asyncio.CancelledError:
                            self.logger.bind(tag=TAG).debug(
                                "Audio send task was cancelled"
                            )
                            raise
                    else:
                        # It is time to send.
                        break

                # Remove the packet from the queue and send it.
                self.queue.popleft()
                self.play_position += self.interval_ms
                try:
                    await send_audio_callback(opus_packet)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to send audio: {e}")
                    raise

        # Mark the queue as empty once all items are processed.
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()
        self._last_queue_empty_time = time.monotonic()

    def start_sending(self, send_audio_callback):
        """
        Start the asynchronous sending task.

        Args:
            send_audio_callback: Callback used to send audio.

        Returns:
            asyncio.Task: The background send task.
        """

        async def _send_loop():
            try:
                while True:
                    # Wait for queued data without busy polling.
                    await self.queue_has_data_event.wait()

                    await self.check_queue(send_audio_callback)
            except asyncio.CancelledError:
                self.logger.bind(tag=TAG).debug("Audio send loop stopped")
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Audio send loop failed: {e}")

        self.pending_send_task = asyncio.create_task(_send_loop())
        return self.pending_send_task

    def stop_sending(self):
        """Stop the background send task."""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            self.logger.bind(tag=TAG).debug("Cancelled audio send task")
