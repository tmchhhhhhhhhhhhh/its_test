import uuid

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

#походу тоже deprecated
class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_verified: bool

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str


class MessageOut(BaseModel):
    message: str
