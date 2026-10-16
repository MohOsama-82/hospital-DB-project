from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
from app.database.crud import (
    create_patient, get_patient_by_id, get_patient_by_user_id,
    list_patients, update_patient, delete_patient, get_staff_by_id
)
from app.schemas.patient import PatientCreate, PatientUpdate, PatientOut
from app.auth.dependencies import get_current_user, require_roles
from app.services.email import send_patient_welcome_email

router = APIRouter(prefix="/patients", tags=["Patients"])


def _check_owns_patient(current_user: dict, patient: dict):
    """A Doctor may only view/edit/delete patients that belong to them.
    Admin bypasses this check entirely."""
    if current_user["role"] == "doctor" and patient.get("created_by") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="You can only access patients assigned to you")


@router.post("/", response_model=PatientOut)
async def add_patient(
    patient: PatientCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_roles("admin", "doctor"))
):
    """
    Doctor: creates the patient and becomes the owner automatically -
    only this doctor will ever see the patient in their list.

    Admin: must pass `assigned_doctor_id` - the patient is owned by that
    doctor (not the admin), and only that doctor will see it.

    Either way, the new patient is emailed their username/password so they
    can sign in and see their own record - sent in the background so a slow
    or unconfigured mail server never delays this response.
    """
    if current_user["role"] == "doctor":
        owner_id = current_user["_id"]
    else:  # admin
        if not patient.assigned_doctor_id:
            raise HTTPException(
                status_code=400,
                detail="assigned_doctor_id is required when an Admin creates a patient"
            )
        assigned_doctor = await get_staff_by_id(patient.assigned_doctor_id)
        if not assigned_doctor or assigned_doctor["role"] != "doctor":
            raise HTTPException(
                status_code=400,
                detail="assigned_doctor_id must belong to an existing Doctor account"
            )
        owner_id = patient.assigned_doctor_id

    created = await create_patient(patient, owner_id)

    background_tasks.add_task(
        send_patient_welcome_email,
        to_email=patient.email,
        patient_name=patient.name,
        username=patient.username,
        password=patient.password,  # plaintext, pre-hash - only used here, never stored
    )

    return created


@router.get("/me", response_model=PatientOut)
async def get_my_patient_record(current_user: dict = Depends(get_current_user)):
    """Patient only. Returns just the caller's own record.
    MUST stay registered before GET /{patient_id}, or "me" gets swallowed
    as if it were a patient_id."""
    if current_user["role"] != "patient":
        raise HTTPException(status_code=403, detail="This endpoint is for patients only")

    patient = await get_patient_by_user_id(current_user["_id"])
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient


@router.get("/", response_model=List[PatientOut])
async def get_all_patients(current_user: dict = Depends(require_roles("admin", "doctor"))):
    """Admin sees every patient. Doctor sees only the patients assigned to them."""
    if current_user["role"] == "doctor":
        return await list_patients(created_by=current_user["_id"])
    return await list_patients()


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(require_roles("admin", "doctor"))
):
    """Admin can look up any patient. Doctor can only look up their own -
    even by direct id, not just from their filtered list."""
    patient = await get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    _check_owns_patient(current_user, patient)
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
async def edit_patient(
    patient_id: str,
    update: PatientUpdate,
    current_user: dict = Depends(require_roles("doctor"))
):
    """Doctor only, and only for their own patients. Admin is intentionally
    NOT allowed to update patient details."""
    existing = await get_patient_by_id(patient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Patient not found")
    _check_owns_patient(current_user, existing)
    return await update_patient(patient_id, update)


@router.delete("/{patient_id}")
async def remove_patient(
    patient_id: str,
    current_user: dict = Depends(require_roles("admin", "doctor"))
):
    """Admin can delete any patient. Doctor can only delete their own."""
    existing = await get_patient_by_id(patient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Patient not found")
    _check_owns_patient(current_user, existing)
    deleted = await delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"message": "Patient deleted successfully"}