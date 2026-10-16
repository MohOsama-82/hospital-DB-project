import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from bson import ObjectId
from bson.errors import InvalidId
from typing import List

import cloudinary.uploader
import cloudinary.utils
from app.services import cloudinary_client  # noqa: F401  (import configures the SDK)

from app.database.connection import patient_files_collection
from app.database.crud import get_patient_by_id, get_patient_by_user_id
from app.schemas.patient import FileOut
from app.auth.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/patients", tags=["Patient Files"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif",
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/webm",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}

SIGNED_URL_TTL_SECONDS = 300  # download links expire 5 minutes after being generated


async def _ensure_patient_exists(patient_id: str):
    try:
        ObjectId(patient_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid patient id")
    patient = await get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# (renamed and takes the patient dict, not just the id):
async def _authorize_access(patient: dict, current_user: dict):
    role = current_user["role"]
    if role == "admin":
        return
    if role == "doctor" and patient.get("created_by") == current_user["_id"]:
        return
    if role == "patient":
        own = await get_patient_by_user_id(current_user["_id"])
        if own and own["_id"] == patient["_id"]:
            return
    raise HTTPException(status_code=403, detail="Not authorized to access these files")


def _serialize_file(doc) -> FileOut:
    return FileOut(
        file_id=str(doc["_id"]),
        filename=doc["filename"],
        content_type=doc.get("content_type"),
        length=doc.get("length", 0),
        upload_date=doc.get("upload_date"),
    )


@router.post("/{patient_id}/files", response_model=FileOut)
async def upload_patient_file(
    patient_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles("admin", "doctor"))
):
    """Admin or Doctor only. Uploads a video/pdf/image/document to Cloudinary
    and stores just the metadata + Cloudinary reference in MongoDB."""
    patient = await _ensure_patient_exists(patient_id)
    await _authorize_access(patient, current_user)
    
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    # type="authenticated" keeps the asset private - it can only be reached
    # with a signed, time-limited URL, never by guessing the plain address.
    result = cloudinary.uploader.upload(
        file.file,
        resource_type="auto",
        type="authenticated",
        folder=f"patients/{patient_id}",
        use_filename=True,
        unique_filename=True,
    )

    doc = {
        "patient_id": patient_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "length": result.get("bytes", 0),
        "upload_date": datetime.utcnow(),
        "cloudinary_public_id": result["public_id"],
        "cloudinary_resource_type": result["resource_type"],
        "uploaded_by": current_user["_id"],
    }
    insert_result = await patient_files_collection.insert_one(doc)
    doc["_id"] = insert_result.inserted_id
    return _serialize_file(doc)


@router.get("/{patient_id}/files", response_model=List[FileOut])
async def list_patient_files(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Admin/Doctor can list any patient's files; a patient can list only their own."""
    patient = await _ensure_patient_exists(patient_id)
    await _authorize_access(patient, current_user)

    files = []
    async for doc in patient_files_collection.find({"patient_id": patient_id}):
        files.append(_serialize_file(doc))
    return files


@router.get("/{patient_id}/files/{file_id}")
async def download_patient_file(
    patient_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Admin/Doctor can download any patient's file; a patient can download only their own.
    Redirects to a short-lived, signed Cloudinary URL - the file is never public."""
    patient = await _ensure_patient_exists(patient_id)
    await _authorize_access(patient, current_user)

    try:
        doc = await patient_files_collection.find_one({"_id": ObjectId(file_id), "patient_id": patient_id})
    except InvalidId:
        doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    signed_url, _ = cloudinary.utils.cloudinary_url(
        doc["cloudinary_public_id"],
        resource_type=doc["cloudinary_resource_type"],
        type="authenticated",
        sign_url=True,
        secure=True,
        expires_at=int(time.time()) + SIGNED_URL_TTL_SECONDS,
    )
    return RedirectResponse(url=signed_url)


@router.delete("/{patient_id}/files/{file_id}")
async def delete_patient_file(
    patient_id: str,
    file_id: str,
    current_user: dict = Depends(require_roles("admin", "doctor"))
):
    """Admin or Doctor."""
    patient = await _ensure_patient_exists(patient_id)
    await _authorize_access(patient, current_user)
    try:
        doc = await patient_files_collection.find_one({"_id": ObjectId(file_id), "patient_id": patient_id})
    except InvalidId:
        doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    cloudinary.uploader.destroy(
        doc["cloudinary_public_id"],
        resource_type=doc["cloudinary_resource_type"],
        type="authenticated",
    )
    await patient_files_collection.delete_one({"_id": doc["_id"]})
    return {"message": "File deleted successfully"}