"""Stats API endpoints."""
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from ..database import get_session, TokenUsage

router = APIRouter()


class TokenUsageResponse(BaseModel):
    year_month: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float

    class Config:
        from_attributes = True


@router.get("/tokens")
async def get_token_usage(year_month: Optional[str] = None):
    """Get token usage statistics."""
    session = get_session()
    try:
        query = session.query(TokenUsage)

        if year_month:
            query = query.filter(TokenUsage.year_month == year_month)
        else:
            # Default to current month
            current_month = datetime.now().strftime("%Y-%m")
            query = query.filter(TokenUsage.year_month == current_month)

        usage = query.all()

        total_input = sum(u.input_tokens for u in usage)
        total_output = sum(u.output_tokens for u in usage)
        total_cost = sum(u.cost_usd for u in usage)

        return {
            "period": year_month or datetime.now().strftime("%Y-%m"),
            "by_model": [TokenUsageResponse.model_validate(u) for u in usage],
            "totals": {
                "input_tokens": total_input,
                "output_tokens": total_output,
                "cost_usd": round(total_cost, 4)
            }
        }
    finally:
        session.close()
