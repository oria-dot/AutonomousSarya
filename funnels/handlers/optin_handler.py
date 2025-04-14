
"""VANTA Funnel Optin Handler"""
from typing import Dict
from core.event_bus import event_bus

async def handle_optin(data: Dict):
    # Emit optin event for audience capture
    event_bus.publish({
        "type": "funnel.optin",
        "data": {
            "email": data["email"],
            "funnel_id": data["funnel_id"],
            "clone_id": data.get("clone_id"),
            "metadata": data
        }
    })
    
    return {"status": "success"}
