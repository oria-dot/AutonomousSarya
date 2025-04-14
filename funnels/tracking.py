
import os
import json
from datetime import datetime
from typing import Optional
import asyncio
import telegram
from supabase import create_client, Client
from fastapi import Request

class FunnelTracker:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.bot = telegram.Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
    async def log_visit(self, request: Request, page: str):
        ip = request.client.host
        timestamp = datetime.now().isoformat()
        
        data = {
            "ip": ip,
            "page": page,
            "timestamp": timestamp,
            "user_agent": request.headers.get("user-agent")
        }
        
        # Store in Supabase
        self.supabase.table("funnel_visits").insert(data).execute()
        
        # Send Telegram alert
        await self.send_telegram_alert(f"New visit to {page} from {ip}")
        
    async def log_conversion(self, event: str, email: Optional[str] = None):
        data = {
            "event": event,
            "email": email,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store conversion
        self.supabase.table("funnel_conversions").insert(data).execute()
        
        # Send conversion alert
        await self.send_telegram_alert(f"New {event} conversion: {email}")
        
    async def send_telegram_alert(self, message: str):
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
        except Exception as e:
            print(f"Telegram alert failed: {str(e)}")
