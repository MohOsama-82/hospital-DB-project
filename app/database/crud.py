from datetime import datetime
from fastapi import HTTPException
from pymongo import ReturnDocument
from app.database.connection import users_collection, patients_collection, appointments_collection, slot_counters_collection
from app.schemas.auth import StaffCreate
from app.schemas.patient import PatientCreate, PatientUpdate
from app.schemas.appointment import GuestAppointmentCreate, PatientAppointmentCreate
from app.auth.utils import get_password_hash


async def get_user_by_email(email: str):
    return await users_collection.find_one({"email": email})

async def get_user_by_username(username: str):
    return await users_collection.find_one({"username": username})

async def get_user_by_id(user_id: str):
    return await users_collection.find_one({"_id": user_id})

async def _insert_user(user_id: str, username: str, email: str, password: str, role: str):
    if await get_user_by_id(user_id):
        raise HTTPException(status_code=400, detail=f"user_id '{user_id}' is already taken, choose another")
    if await get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await get_user_by_username(username):
        raise HTTPException(status_code=400, detail=f"Username '{username}' is already taken, choose another")

    user_dict = {
        "_id": user_id,
        "username": username,
        "email": email,
        "hashed_password": get_password_hash(password),
        "role": role,
        "is_active": True,
        "status": "active",
        "created_at": datetime.utcnow(),
    }
    await users_collection.insert_one(user_dict)
    created_user = await users_collection.find_one({"_id": user_id})
    return created_user

async def create_staff(staff: StaffCreate):
    return await _insert_user(staff.user_id, staff.username, staff.email, staff.password, staff.role)

async def list_staff():
    cursor = users_collection.find({"role": {"$in": ["doctor", "admin"]}})
    return [doc async for doc in cursor]

async def get_staff_by_id(user_id: str):
    doc = await get_user_by_id(user_id)
    if doc and doc["role"] in ("doctor", "admin"):
        return doc
    return None


async def create_patient(patient: PatientCreate, created_by_id: str):
    user = await _insert_user(patient.user_id, patient.username, patient.email, patient.password, "patient")

    patient_dict = patient.dict(exclude={"user_id", "username", "password"})
    patient_dict["user_id"] = user["_id"]
    patient_dict["username"] = user["username"]
    patient_dict["created_by"] = created_by_id
    patient_dict["created_at"] = datetime.utcnow()

    result = await patients_collection.insert_one(patient_dict)
    created = await patients_collection.find_one({"_id": result.inserted_id})
    return _serialize_patient(created)

def _serialize_patient(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    doc["user_id"] = str(doc["user_id"])
    if doc.get("created_by"):
        doc["created_by"] = str(doc["created_by"])
    return doc

async def get_patient_by_id(patient_id: str):
    from bson import ObjectId
    doc = await patients_collection.find_one({"_id": ObjectId(patient_id)})
    return _serialize_patient(doc)

async def get_patient_by_user_id(user_id: str):
    doc = await patients_collection.find_one({"user_id": user_id})
    return _serialize_patient(doc)

async def update_patient(patient_id: str, update: PatientUpdate):
    from bson import ObjectId
    update_data = {k: v for k, v in update.dict(exclude_unset=True).items() if v is not None}
    if not update_data:
        return await get_patient_by_id(patient_id)

    result = await patients_collection.find_one_and_update(
        {"_id": ObjectId(patient_id)},
        {"$set": update_data},
        return_document=True
    )
    return _serialize_patient(result)

async def delete_patient(patient_id: str):
    from bson import ObjectId
    import cloudinary.uploader
    from app.database.connection import patient_files_collection

    patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
    if not patient:
        return False

    async for f in patient_files_collection.find({"patient_id": patient_id}):
        cloudinary.uploader.destroy(
            f["cloudinary_public_id"],
            resource_type=f["cloudinary_resource_type"],
            type="authenticated",
        )
    await patient_files_collection.delete_many({"patient_id": patient_id})

    await patients_collection.delete_one({"_id": ObjectId(patient_id)})
    await users_collection.delete_one({"_id": patient["user_id"]})
    return True

async def delete_staff(user_id: str):
    staff = await get_staff_by_id(user_id)
    if not staff:
        return False
    await users_collection.delete_one({"_id": user_id})
    return True

async def update_staff(user_id: str, update):
    staff = await get_staff_by_id(user_id)
    if not staff:
        return None

    update_data = {k: v for k, v in update.dict(exclude_unset=True).items() if v is not None}
    if not update_data:
        return staff

    if "email" in update_data:
        existing = await get_user_by_email(update_data["email"])
        if existing and existing["_id"] != user_id:
            raise HTTPException(status_code=400, detail="Email already registered to another account")

    # Resigning/reinstating a staff member stamps (or clears) resigned_at
    # automatically - the Admin only ever picks the status, not the date.
    if update_data.get("status") == "resigned":
        update_data["resigned_at"] = datetime.utcnow()
    elif update_data.get("status") == "active":
        update_data["resigned_at"] = None

    await users_collection.update_one({"_id": user_id}, {"$set": update_data})
    return await get_staff_by_id(user_id)

async def list_patients(created_by: str = None):
    query = {"created_by": created_by} if created_by else {}
    cursor = patients_collection.find(query)
    return [_serialize_patient(doc) async for doc in cursor]


# ---------- Appointments ----------

def _serialize_appointment(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc

async def count_slot_bookings(doctor_id: str, appointment_date: str, appointment_time: str) -> int:
    """How many patients are currently (not cancelled) queued in this exact
    slot. A slot is never "full" - this is shown as a queue count, not used
    to block new bookings."""
    return await appointments_collection.count_documents({
        "doctor_id": doctor_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "status": "booked",
    })

async def _next_token_number(doctor_id: str, appointment_date: str, appointment_time: str) -> int:
    """Atomically hands out the next queue position (1, 2, 3...) for this
    doctor/date/time slot. Uses a $inc on a per-slot counter document so two
    patients booking the same slot at the same instant never get the same
    number - no patient "holds" the slot itself, they just get a position in
    line for it. Numbers are never reused, even after a cancellation."""
    key = f"{doctor_id}|{appointment_date}|{appointment_time}"
    counter = await slot_counters_collection.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return counter["seq"]

async def create_guest_appointment(appt: GuestAppointmentCreate):
    """A brand-new patient booking without an account. Their name/gender/contact
    are exactly what they typed in - no patient profile is created. Gets the
    next token number in the slot's queue; the slot itself is never exclusive."""
    doc = appt.dict()
    doc["patient_id"] = None
    doc["is_guest"] = True
    doc["status"] = "booked"
    doc["seen_by_doctor"] = False
    doc["created_at"] = datetime.utcnow()
    doc["token_number"] = await _next_token_number(appt.doctor_id, appt.appointment_date, appt.appointment_time)
    result = await appointments_collection.insert_one(doc)
    created = await appointments_collection.find_one({"_id": result.inserted_id})
    return _serialize_appointment(created)

async def create_patient_appointment(appt: PatientAppointmentCreate, patient: dict):
    """An already-registered, logged-in patient booking. Name/contact are
    pulled from their existing profile, not re-typed. Gets the next token
    number in the slot's queue; the slot itself is never exclusive."""
    doc = appt.dict()
    doc["patient_id"] = patient["_id"]
    doc["name"] = patient["name"]
    doc["gender"] = None  # the core Patient profile doesn't collect gender
    doc["contact"] = patient["contact"]
    doc["email"] = patient.get("email")
    doc["is_guest"] = False
    doc["status"] = "booked"
    doc["seen_by_doctor"] = False
    doc["created_at"] = datetime.utcnow()
    doc["token_number"] = await _next_token_number(appt.doctor_id, appt.appointment_date, appt.appointment_time)
    result = await appointments_collection.insert_one(doc)
    created = await appointments_collection.find_one({"_id": result.inserted_id})
    return _serialize_appointment(created)

async def count_unseen_appointments(doctor_id: str = None):
    """How many booked appointments haven't been viewed yet. Doctor gets their
    own count; Admin (doctor_id=None) gets the count across every doctor."""
    query = {"status": "booked", "seen_by_doctor": False}
    if doctor_id:
        query["doctor_id"] = doctor_id
    return await appointments_collection.count_documents(query)

async def mark_appointments_seen(doctor_id: str = None):
    """Clears the unseen badge - called when the Appointments tab is opened."""
    query = {"status": "booked", "seen_by_doctor": False}
    if doctor_id:
        query["doctor_id"] = doctor_id
    result = await appointments_collection.update_many(query, {"$set": {"seen_by_doctor": True}})
    return result.modified_count

async def list_doctor_appointments(doctor_id: str, appointment_date: str = None):
    """Only this doctor's appointments (booked or accepted - cancelled ones
    drop off the list), optionally on one date."""
    query = {"doctor_id": doctor_id, "status": {"$ne": "cancelled"}}
    if appointment_date:
        query["appointment_date"] = appointment_date
    cursor = appointments_collection.find(query).sort([("appointment_time", 1), ("token_number", 1)])
    return [_serialize_appointment(doc) async for doc in cursor]

async def list_all_appointments(appointment_date: str = None):
    """Every doctor's appointments (booked or accepted) - Admin only, view-only."""
    query = {"status": {"$ne": "cancelled"}}
    if appointment_date:
        query["appointment_date"] = appointment_date
    cursor = appointments_collection.find(query).sort(
        [("appointment_date", 1), ("appointment_time", 1), ("token_number", 1)]
    )
    return [_serialize_appointment(doc) async for doc in cursor]

async def accept_appointment(appointment_id: str, current_user: dict):
    """Doctor-only: confirms a pending booking. Only the owning doctor can
    accept it, and only while it's still 'booked' (not already accepted or
    cancelled). Returns the updated appointment doc (or None if not found)
    so the caller has what it needs to send a confirmation email."""
    from bson import ObjectId
    appt = await appointments_collection.find_one({"_id": ObjectId(appointment_id)})
    if not appt:
        return None
    if appt["doctor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="You can only accept your own appointments")
    if appt["status"] != "booked":
        raise HTTPException(status_code=400, detail=f"This appointment is already {appt['status']}")
    await appointments_collection.update_one(
        {"_id": ObjectId(appointment_id)}, {"$set": {"status": "accepted"}}
    )
    updated = await appointments_collection.find_one({"_id": ObjectId(appointment_id)})
    return _serialize_appointment(updated)

async def cancel_appointment(appointment_id: str, current_user: dict):
    """Doctor-only: cancels one of their own appointments. Admin cannot
    cancel or accept appointments - view-only for Admin, by design."""
    from bson import ObjectId
    appt = await appointments_collection.find_one({"_id": ObjectId(appointment_id)})
    if not appt:
        return False
    if appt["doctor_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="You can only cancel your own appointments")
    await appointments_collection.update_one(
        {"_id": ObjectId(appointment_id)}, {"$set": {"status": "cancelled"}}
    )
    return True