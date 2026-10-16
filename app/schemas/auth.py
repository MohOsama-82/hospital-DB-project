from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime
from app.schemas.helpers import PyObjectId

# Used internally when we create the login account behind a Patient record.
# Never exposed directly on a public "self-signup" route.
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)
    role: Literal["admin", "doctor", "patient"] = "patient"

# Used by an Admin to create a Doctor or Admin account.
# user_id is the manually chosen internal account ID (e.g. "6a574e0cd42f...", or
# any string the Admin picks) - this becomes the record's real ID in the database.
# username is the separate, already-working login name - untouched.
class StaffCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, description="Manually chosen account ID")
    username: str = Field(..., min_length=3, max_length=50, description="Manually chosen login name, e.g. DOC001")
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)
    role: Literal["doctor", "admin"]

# Admin-only. Every field optional so an Admin can send just what changed.
# Deliberately excludes username/password - those aren't editable through
# this endpoint to avoid accidentally locking someone out of their own login.
class StaffUpdate(BaseModel):
    email: Optional[str] = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    role: Optional[Literal["doctor", "admin"]] = None
    status: Optional[Literal["active", "resigned"]] = Field(
        None, description="Set to 'resigned' to mark the account inactive without deleting it."
    )

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserOut(BaseModel):
    id: str = Field(alias="_id")
    email: str
    username: str
    role: str
    status: str = "active"
    created_at: Optional[datetime] = None
    resigned_at: Optional[datetime] = None

    model_config = ConfigDict(
        validate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str}
    )