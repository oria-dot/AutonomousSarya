
"""VANTA Auto-Audience Capture System"""
from typing import Dict, Optional
from core.base_module import BaseModule
from core.event_bus import event_bus
from database import get_db

class AudienceCapture(BaseModule):
    def __init__(self):
        super().__init__("AudienceCapture")
        self.db = get_db()

    def _initialize(self) -> bool:
        event_bus.subscribe("funnel.optin", self._handle_optin)
        event_bus.subscribe("gumroad.purchase", self._handle_purchase)
        event_bus.subscribe("saas.signup", self._handle_signup)
        return True

    def _start(self) -> bool:
        return True

    def _stop(self) -> bool:
        return True

    async def capture_contact(self, data: Dict, source: str) -> bool:
        try:
            contact = {
                "email": data["email"],
                "source": source,
                "metadata": data,
                "status": "active"
            }
            await self.db.table("audience_contacts").insert(contact)
            
            # Emit reflex signal
            event_bus.publish({
                "type": "reflex.signal",
                "data": {
                    "type": "audience_capture",
                    "clone_id": data.get("clone_id"),
                    "intensity": 0.6,
                    "trigger": f"contact_captured_from_{source}",
                    "response": contact
                }
            })
            return True
        except Exception as e:
            self.logger.error(f"Contact capture failed: {str(e)}")
            return False

    async def _handle_optin(self, event: Dict) -> None:
        await self.capture_contact(event["data"], "funnel")

    async def _handle_purchase(self, event: Dict) -> None:
        await self.capture_contact(event["data"], "gumroad")

    async def _handle_signup(self, event: Dict) -> None:
        await self.capture_contact(event["data"], "saas")

audience_capture = AudienceCapture()
