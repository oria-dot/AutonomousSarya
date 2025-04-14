
from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel
from typing import Dict

from api.auth import User, get_current_active_user
from affiliate_system.affiliate_engine import affiliate_engine

router = APIRouter(
    prefix="/affiliate",
    tags=["Affiliate"],
    responses={404: {"description": "Not found"}}
)

class AffiliateRequest(BaseModel):
    influencer_id: str

@router.post("/create")
async def create_affiliate_link(
    request: AffiliateRequest,
    current_user: User = Security(get_current_active_user, scopes=["write"])
):
    """Generate new affiliate link."""
    link = affiliate_engine.generate_affiliate_link(request.influencer_id)
    return {"affiliate_link": link}

@router.get("/stats/{ref_code}")
async def get_affiliate_stats(
    ref_code: str,
    current_user: User = Security(get_current_active_user, scopes=["read"])
):
    """Get affiliate statistics."""
    stats = await affiliate_engine.get_affiliate_stats(ref_code)
    return stats
