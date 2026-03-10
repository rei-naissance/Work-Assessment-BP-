from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


def _normalize_email(v: str) -> str:
    return v.strip().lower()


class User(BaseModel):
    email: EmailStr
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return _normalize_email(v)


class OTPRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return _normalize_email(v)


class OTPVerify(BaseModel):
    email: EmailStr
    code: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return _normalize_email(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    is_admin: bool
    created_at: Optional[datetime] = None
