from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BinderRequest(BaseModel):
    tier: str = "standard"  # "standard" ($59.99) or "premium" ($99)


class Binder(BaseModel):
    user_id: str
    tier: str = "standard"
    profile_snapshot: dict = {}
    modules: list[str] = []
    pdf_path: Optional[str] = None
    status: str = "pending"  # pending, generating, ready, failed
    ai_content: dict = {}
    ai_draft: dict = {}
    missing_items: dict = {}  # AI-identified gaps per section
    ai_tokens_used: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BinderOut(BaseModel):
    id: str
    user_id: str
    tier: str = "standard"
    modules: list[str] = []
    status: str
    ai_content: dict = {}
    missing_items: dict = {}
    created_at: Optional[datetime] = None
