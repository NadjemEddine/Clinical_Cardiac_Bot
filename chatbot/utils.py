# shared_state.py
import asyncio

# Global dictionary to store request_id -> {event, result}
response_events = {}