"""Feedback routes for bug reports, suggestions, and questions."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from jose import jwt, JWTError

from app.config import settings
from app.errors import handle_db_error

router = APIRouter()


class FeedbackRequest(BaseModel):
    type: str = Field(max_length=20)  # bug, feedback, question
    message: str = Field(max_length=5000)
    page: Optional[str] = None


def get_user_from_token(request: Request) -> Optional[dict]:
    """Try to get user from token, return None if not authenticated."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"user_id": payload["sub"], "email": payload.get("email", "")}
    except JWTError:
        return None


@router.post("")
async def submit_feedback(request: Request, body: FeedbackRequest):
    """Submit user feedback. Works for both authenticated and anonymous users."""
    db = request.app.state.db
    user = get_user_from_token(request)

    feedback_doc = {
        "type": body.type,
        "message": body.message,
        "page": body.page,
        "user_id": user.get("user_id") if user else None,
        "user_email": user.get("email") if user else None,
        "user_agent": request.headers.get("user-agent"),
        "created_at": datetime.utcnow(),
        "status": "new",  # new, reviewed, resolved
    }

    try:
        await db.feedback.insert_one(feedback_doc)
    except Exception as e:
        handle_db_error("inserting feedback", e)

    return {"success": True, "message": "Feedback received"}
