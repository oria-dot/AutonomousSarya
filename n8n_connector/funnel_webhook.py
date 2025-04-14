
import os
import aiohttp
import json
from typing import Dict, Any

class N8NWebhook:
    def __init__(self):
        self.webhook_url = os.getenv("N8N_WEBHOOK_URL")
        
    async def trigger_event(self, event_type: str, data: Dict[str, Any]):
        payload = {
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.webhook_url, json=payload) as response:
                    return await response.json()
            except Exception as e:
                print(f"N8N webhook failed: {str(e)}")
                return None
