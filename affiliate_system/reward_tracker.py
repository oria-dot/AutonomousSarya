
from datetime import datetime
from typing import Dict, Optional
import os
from supabase import create_client, Client
import telegram
from core.base_module import BaseModule

class RewardTracker(BaseModule):
    def __init__(self):
        super().__init__("RewardTracker")
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.bot = telegram.Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
    async def log_referral(self, ref_code: str, event_type: str, data: Optional[Dict] = None):
        log_data = {
            "ref_code": ref_code,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        # Store in Supabase
        self.supabase.table("referral_stats").insert(log_data).execute()
        
        # Check thresholds
        stats = await self.get_stats(ref_code)
        if stats["conversions"] >= 10:
            await self.send_telegram_alert(
                f"🎉 Affiliate {ref_code} hit 10 conversions!"
            )
            
    async def get_stats(self, ref_code: str) -> Dict:
        results = self.supabase.table("referral_stats")\
            .select("*")\
            .eq("ref_code", ref_code)\
            .execute()
            
        stats = {
            "clicks": 0,
            "optins": 0, 
            "conversions": 0,
            "revenue": 0.0
        }
        
        for row in results.data:
            event_type = row["event_type"]
            stats[event_type] += 1
            if event_type == "conversion":
                stats["revenue"] += float(row["data"].get("amount", 0))
                
        return stats
        
    async def send_telegram_alert(self, message: str):
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
        except Exception as e:
            print(f"Telegram alert failed: {str(e)}")
