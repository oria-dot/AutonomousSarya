
"""VANTA Audience API Endpoints"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from audience_system.audience_capture import audience_capture
from audience_system.email_followup_engine import email_followup_engine

router = APIRouter(prefix="/audience")

@router.post("/add")
async def add_contact(data: Dict):
    success = await audience_capture.capture_contact(data, data.get("source", "api"))
    if not success:
        raise HTTPException(status_code=500, message="Failed to add contact")
    return {"status": "success"}

@router.get("/list")
async def list_contacts():
    db = get_db()
    contacts = await db.table("audience_contacts").select("*").execute()
    return contacts

@router.post("/send_campaign")
async def send_campaign(campaign_data: Dict):
    campaign = email_followup_engine.campaigns.get(campaign_data["campaign_id"])
    if not campaign:
        raise HTTPException(status_code=404, message="Campaign not found")
    
    # Schedule campaign emails
    return {"status": "scheduled"}
