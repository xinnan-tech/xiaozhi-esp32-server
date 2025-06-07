import asyncio
from dataclasses import dataclass

@dataclass
class VisualContextEvent:
    """
    Represents an event carrying visual context information.
    """
    device_id: str
    client_id: str  # Added client_id as it's available in VisionHandler and might be useful
    text: str

# Global queue to act as a simple event bus for visual context events
visual_context_event_queue = asyncio.Queue()

async def publish_visual_context_event(device_id: str, client_id: str, text: str):
    """
    Publishes a visual context event to the queue.
    """
    event = VisualContextEvent(device_id=device_id, client_id=client_id, text=text)
    await visual_context_event_queue.put(event)

async def consume_visual_context_event() -> VisualContextEvent:
    """
    Consumes a visual context event from the queue.
    This will block until an event is available.
    """
    event = await visual_context_event_queue.get()
    return event

# Example of how a consumer might use this:
# async def event_consumer_example(device_id_to_listen_for: str):
#     while True:
#         print(f"Consumer for {device_id_to_listen_for} waiting for event...")
#         event = await consume_visual_context_event()
#         if event.device_id == device_id_to_listen_for:
#             print(f"Consumer for {device_id_to_listen_for} received: {event.text}")
#         else:
#             # Not our event, put it back if other consumers might need it
#             # or if there's a central dispatcher. For a simple queue with
#             # specific consumers, this might not be ideal.
#             # A more robust pub/sub would handle routing.
#             print(f"Consumer for {device_id_to_listen_for} ignored event for {event.device_id}")
#             # For now, we'll assume direct consumption or a dispatcher will handle filtering.
#             # If putting back: await visual_context_event_queue.put(event)
#             pass
