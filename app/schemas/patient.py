from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional,Literal
from datetime import datetime
from app.schemas.helpers import PyObjectId

# Full standard ABO/Rh blood group set - the 8 groups a hospital actually
# transfuses by. Kept as one shared type so Create and Update can't drift.
BloodGroup = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
class PatientBase(BaseModel):
    
    name: str = Field(..., min_length=1, max_length=100)
    contact: str = Field(..., description="Patient's own phone number")
    relative_contact: str = Field(..., description="Emergency / relative phone number")
    age: int = Field(..., ge=0, le=150)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    blood_group: str = Field(..., description="e.g. A+, O-, AB+")

# Filled in by Admin or Doctor when creating a new patient.
# user_id is the manually chosen internal account ID for the patient's login
# (e.g. "6a574e0cd42f...", or any string) - this becomes that account's real
# ID in the database. username is the separate, already-working login name.
class PatientCreate(PatientBase):
    user_id: str = Field(..., min_length=1, max_length=100, description="Manually chosen account ID")
    username: str = Field(..., min_length=3, max_length=50, description="Manually chosen login name, e.g. PAT001")
    password: str = Field(..., min_length=8)

    # ADD THIS:
    assigned_doctor_id: Optional[str] = Field(
        None,
        description="Doctor who will own this patient. Required if the creator is an Admin."
    )

# Only a Doctor is allowed to call the update endpoint using this schema.
# Every field optional so a doctor can send just what changed.
class PatientUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    relative_contact: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    email: Optional[str] = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    blood_group: Optional[str] = None
    discharge_date: Optional[str] = Field(None, description="YYYY-MM-DD. Set by the treating Doctor when the patient is discharged.")

class PatientOut(PatientBase):
    id: str = Field(alias="_id")
    user_id: str
    username: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    discharge_date: Optional[str] = None

    model_config = ConfigDict(
        validate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str}
    )

class FileOut(BaseModel):
    file_id: str
    filename: str
    content_type: Optional[str] = None
    length: int
    upload_date: Optional[datetime] = None