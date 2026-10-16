from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional

from app.database.crud import (
    get_staff_by_id, get_patient_by_user_id, list_staff,
    create_guest_appointment, create_patient_appointment,
    count_slot_bookings, list_doctor_appointments, list_all_appointments,accept_appointment,
    cancel_appointment, count_unseen_appointments, mark_appointments_seen,
)
from app.schemas.appointment import GuestAppointmentCreate, PatientAppointmentCreate, AppointmentOut
from app.auth.dependencies import require_roles
from app.services.email import send_appointment_confirmation_email

router = APIRouter(prefix="/appointments", tags=["Appointments"])

# Clinic hours used to generate the day's bookable 30-minute slots.
# Adjust these two constants if the real hours differ.
CLINIC_START = "09:00"
CLINIC_END = "17:00"
SLOT_MINUTES = 10


def _generate_day_slots():
    """['09:00', '09:30', '10:00', ... up to but excluding CLINIC_END]."""
    slots = []
    cur = datetime.strptime(CLINIC_START, "%H:%M")
    end = datetime.strptime(CLINIC_END, "%H:%M")
    while cur < end:
        slots.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=SLOT_MINUTES)
    return slots


def _allowed_booking_dates():
    """Bookings only open for today and tomorrow - ['2026-08-14', '2026-08-15']."""
    today = datetime.utcnow().date()
    return [today.strftime("%Y-%m-%d"), (today + timedelta(days=1)).strftime("%Y-%m-%d")]


def _assert_bookable_date(appointment_date: str):
    if appointment_date not in _allowed_booking_dates():
        raise HTTPException(status_code=400, detail="Appointments can only be booked for today or tomorrow")


@router.get("/doctors")
async def list_bookable_doctors():
    """Public - no login required. Just enough info to populate a doctor
    picker on the guest booking form (a brand-new patient hasn't signed in yet)."""
    staff = await list_staff()
    return [{"user_id": s["_id"], "username": s["username"]} for s in staff if s["role"] == "doctor"]


@router.get("/available-dates")
async def get_available_dates():
    """Public. The only two dates bookings are open for - today and tomorrow."""
    dates = _allowed_booking_dates()
    return [{"date": dates[0], "label": "Today"}, {"date": dates[1], "label": "Tomorrow"}]


@router.get("/available-slots")
async def get_available_slots(doctor_id: str, appointment_date: str = Query(..., description="YYYY-MM-DD")):
    """Public. Every slot is always bookable - a slot is a queue, not a single
    seat. Returns how many patients are already queued in each slot so the
    next patient knows what token number they'd get (queue_count + 1)."""
    doctor = await get_staff_by_id(doctor_id)
    if not doctor or doctor["role"] != "doctor":
        raise HTTPException(status_code=404, detail="Doctor not found")
    _assert_bookable_date(appointment_date)

    all_slots = _generate_day_slots()
    result = []
    for t in all_slots:
        booked_count = await count_slot_bookings(doctor_id, appointment_date, t)
        result.append({"time": t, "booked_count": booked_count, "next_token": booked_count + 1})
    return result


@router.post("/guest", response_model=AppointmentOut)
async def book_guest_appointment(appt: GuestAppointmentCreate):
    """Public. A brand-new patient books without logging in - they type their
    own name/gender/contact and pick a doctor, date, and 10-minute slot.
    Slots are a queue: booking an already-booked slot is fine, the patient
    just gets the next token number in line rather than exclusive ownership
    of that time."""
    if appt.appointment_time not in _generate_day_slots():
        raise HTTPException(status_code=400, detail="Appointment time must land on a 10-minute clinic slot")
    _assert_bookable_date(appt.appointment_date)

    doctor = await get_staff_by_id(appt.doctor_id)
    if not doctor or doctor["role"] != "doctor":
        raise HTTPException(status_code=400, detail="Selected doctor does not exist")

    result = await create_guest_appointment(appt)
    result["doctor_username"] = doctor["username"]
    return result


@router.post("/", response_model=AppointmentOut)
async def book_patient_appointment(
    appt: PatientAppointmentCreate,
    current_user: dict = Depends(require_roles("patient"))
):
    """Patient only, must be logged in. Uses their existing profile - no
    need to re-type name/contact. Slots are a queue: booking an
    already-booked slot is fine, the patient just gets the next token
    number in line rather than exclusive ownership of that time."""
    if appt.appointment_time not in _generate_day_slots():
        raise HTTPException(status_code=400, detail="Appointment time must land on a 10-minute clinic slot")
    _assert_bookable_date(appt.appointment_date)

    patient = await get_patient_by_user_id(current_user["_id"])
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    doctor = await get_staff_by_id(appt.doctor_id)
    if not doctor or doctor["role"] != "doctor":
        raise HTTPException(status_code=400, detail="Selected doctor does not exist")

    result = await create_patient_appointment(appt, patient)
    result["doctor_username"] = doctor["username"]
    return result


@router.get("/", response_model=List[AppointmentOut])
async def list_appointments(
    appointment_date: Optional[str] = None,
    current_user: dict = Depends(require_roles("admin", "doctor"))
):
    """Admin sees every appointment. Doctor sees only their own."""
    if current_user["role"] == "doctor":
        return await list_doctor_appointments(current_user["_id"], appointment_date)
    return await list_all_appointments(appointment_date)


@router.post("/{appointment_id}/accept")
async def accept_appointment_row(
    appointment_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_roles("doctor"))
):
    """Doctor-only - confirms a pending booking. Admin has no accept/cancel
    action on appointments at all; view-only for Admin by design. Sends a
    confirmation email to the patient in the background so the response
    isn't held up by SMTP."""
    accepted = await accept_appointment(appointment_id, current_user)
    if not accepted:
        raise HTTPException(status_code=404, detail="Appointment not found")

    doctor = await get_staff_by_id(current_user["_id"])
    background_tasks.add_task(
        send_appointment_confirmation_email,
        to_email=accepted.get("email"),
        patient_name=accepted["name"],
        doctor_username=doctor["username"] if doctor else current_user["_id"],
        appointment_date=accepted["appointment_date"],
        appointment_time=accepted["appointment_time"],
        token_number=accepted["token_number"],
    )
    
    return {"message": "Appointment accepted"}


@router.delete("/{appointment_id}")
async def remove_appointment(
    appointment_id: str,
    current_user: dict = Depends(require_roles("admin", "doctor"))
):
    """Doctor-only - cancels one of their own appointments. Admin has no
    accept/cancel action on appointments at all; view-only for Admin by design."""
    cancelled = await cancel_appointment(appointment_id, current_user)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": "Appointment cancelled"}


@router.get("/unseen-count")
async def get_unseen_count(current_user: dict = Depends(require_roles("admin", "doctor"))):
    """Powers the notification badge on the Appointments nav item.
    Doctor gets their own unseen count; Admin gets the total across everyone."""
    doctor_id = current_user["_id"] if current_user["role"] == "doctor" else None
    count = await count_unseen_appointments(doctor_id)
    return {"count": count}


@router.post("/mark-seen")
async def mark_seen(current_user: dict = Depends(require_roles("admin", "doctor"))):
    """Clears the badge - call this when the Appointments tab is opened."""
    doctor_id = current_user["_id"] if current_user["role"] == "doctor" else None
    marked = await mark_appointments_seen(doctor_id)
    return {"marked": marked}