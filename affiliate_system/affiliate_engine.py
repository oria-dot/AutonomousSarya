
import uuid
from datetime import datetime
from typing import Dict, Optional

from core.base_module import BaseModule
from affiliate_system.reward_tracker import RewardTracker

class AffiliateEngine(BaseModule):
    def __init__(self):
        super().__init__("AffiliateEngine")
        self.reward_tracker = RewardTracker()
        
    def generate_affiliate_link(self, influencer_id: str) -> str:
        ref_code = str(uuid.uuid4())[:8]
        return f"/funnel/optin?ref={ref_code}"
        
    async def track_referral(self, ref_code: str, event_type: str, data: Optional[Dict] = None):
        await self.reward_tracker.log_referral(ref_code, event_type, data)
        
    async def get_affiliate_stats(self, ref_code: str) -> Dict:
        return await self.reward_tracker.get_stats(ref_code)

affiliate_engine = AffiliateEngine()
