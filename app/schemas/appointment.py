from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from app.schemas.helpers import PyObjectId


class AppointmentBase(BaseModel):
    doctor_id: str = Field(..., description="The doctor's user_id")
    appointment_date: str = Field(..., description="YYYY-MM-DD")
    appointment_time: str = Field(..., description="HH:MM, 24h, must land on a 10-minute clinic slot")


# A brand-new patient booking without an account. They type their own
# name/gender/contact/email directly on the booking form.
class GuestAppointmentCreate(AppointmentBase):
    name: str = Field(..., min_length=1, max_length=100)
    gender: Literal["male", "female", "other"]
    contact: str = Field(..., min_length=5, max_length=20)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')


# An already-registered patient, logged in. Name/contact/email come from their
# existing profile - nothing else to type beyond doctor/date/time.
class PatientAppointmentCreate(AppointmentBase):
    pass


class AppointmentOut(BaseModel):
    id: str = Field(alias="_id")
    doctor_id: str
    doctor_username: Optional[str] = None
    patient_id: Optional[str] = None
    name: str
    gender: Optional[str] = None
    contact: str
    email: Optional[str] = None
    appointment_date: str
    appointment_time: str
    token_number: int
    status: str
    is_guest: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(
        validate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str}
    )