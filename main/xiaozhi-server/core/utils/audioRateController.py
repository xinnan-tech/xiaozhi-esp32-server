import time
import asyncio
from collections import deque
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class AudioRateController:
    """
    Audio Rate Controller - Precisely controls audio sending based on 60ms frame duration
    Solves time accumulation error in high concurrency
    """

    def __init__(self, frame_duration=60):
        """
        Args:
            frame_duration: Duration of a single audio frame (ms), default 60ms
        """
        self.frame_duration = frame_duration
        self.queue = deque()
        self.play_position = 0  # Virtual playback position (ms)
        self.start_timestamp = None  # Start timestamp (read-only, not modified)
        self.pending_send_task = None
        self.logger = logger
        self.queue_empty_event = asyncio.Event()  # Queue empty event
        self.queue_empty_event.set()  # Initial state is empty
        self.queue_has_data_event = asyncio.Event()  # Queue has data event

    def reset(self):
        """Reset controller state"""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            # After cancelling task, it will be cleaned up in next event loop, no need to block wait

        self.queue.clear()
        self.play_position = 0
        self.start_timestamp = None  # Set by the first audio packet
        # Event handling
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()

    def add_audio(self, opus_packet):
        """Add audio packet to queue"""
        self.queue.append(("audio", opus_packet))
        # Event handling
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def add_message(self, message_callback):
        """
        Add message to queue (send immediately, does not consume playback time)

        Args:
            message_callback: Message sending callback function async def()
        """
        self.queue.append(("message", message_callback))
        # Event handling
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def _get_elapsed_ms(self):
        """Get elapsed time (ms)"""
        if self.start_timestamp is None:
            return 0
        return (time.monotonic() - self.start_timestamp) * 1000

    async def check_queue(self, send_audio_callback):
        """
        Check queue and send audio/message on time

        Args:
            send_audio_callback: Audio sending callback function async def(opus_packet)
        """
        while self.queue:
            item = self.queue[0]
            item_type = item[0]

            if item_type == "message":
                # Message type: send immediately, does not consume playback time
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

                # Loop wait until time is up
                while True:
                    # Calculate time difference
                    elapsed_ms = self._get_elapsed_ms()
                    output_ms = self.play_position

                    if elapsed_ms < output_ms:
                        # Not time to send yet, calculate wait duration
                        wait_ms = output_ms - elapsed_ms

                        # Continue check after wait (allow interruption)
                        try:
                            await asyncio.sleep(wait_ms / 1000)
                        except asyncio.CancelledError:
                            self.logger.bind(tag=TAG).debug("Audio sending task cancelled")
                            raise
                        # Re-check time after wait (loop back to while True)
                    else:
                        # Time is up, break wait loop
                        break

                # Time is up, remove from queue and send
                self.queue.popleft()
                self.play_position += self.frame_duration
                try:
                    await send_audio_callback(opus_packet)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to send audio: {e}")
                    # Do not re-raise to prevent killing the loop
                    # raise

        # Clear events after processing queue
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()

    def start_sending(self, send_audio_callback):
        """
        Start asynchronous sending task

        Args:
            send_audio_callback: Audio sending callback function

        Returns:
            asyncio.Task: Sending task
        """

        async def _send_loop():
            try:
                while True:
                    # Wait for queue data event, do not poll to save CPU
                    await self.queue_has_data_event.wait()

                    await self.check_queue(send_audio_callback)
            except asyncio.CancelledError:
                self.logger.bind(tag=TAG).debug("Audio sending loop stopped")
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Audio send loop exception: {e}")
            finally:
                # Ensure event is set so waiters don't hang
                self.queue_empty_event.set()
                self.logger.bind(tag=TAG).debug("Audio send loop exited, queue_empty_event set")

        self.pending_send_task = asyncio.create_task(_send_loop())
        return self.pending_send_task

    def stop_sending(self):
        """Stop sending task"""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            self.logger.bind(tag=TAG).debug("Audio sending task cancelled")
