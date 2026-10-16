from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.database.crud import get_user_by_username, create_staff, list_staff, get_staff_by_id, delete_staff, update_staff
from app.schemas.auth import StaffCreate, StaffUpdate, UserLogin, Token, UserOut
from app.auth.utils import verify_password, create_access_token
from app.auth.dependencies import require_roles

router = APIRouter(prefix="/auth", tags=["Authentication"])

# NOTE: There is intentionally no public "/register" route.
# Nobody can create their own account:
#   - Doctor/Admin accounts -> only an existing Admin, via /auth/create-staff
#   - Patient accounts      -> only Admin/Doctor, via POST /patients/
# The very first Admin must be bootstrapped directly in the database
# (see scripts/create_admin.py).

@router.post("/create-staff", response_model=UserOut)
async def create_staff_account(
    staff: StaffCreate,
    current_user: dict = Depends(require_roles("admin"))
):
    """Admin-only. Creates a Doctor or Admin login account."""
    return await create_staff(staff)

@router.get("/staff", response_model=List[UserOut])
async def view_all_staff(current_user: dict = Depends(require_roles("admin"))):
    """Admin-only. Lists every Doctor and Admin account (patients are never included)."""
    return await list_staff()

@router.get("/staff/{user_id}", response_model=UserOut)
async def view_staff_member(
    user_id: str,
    current_user: dict = Depends(require_roles("admin"))
):
    """Admin-only. Look up a single Doctor/Admin by their user_id."""
    staff = await get_staff_by_id(user_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return staff

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    db_user = await get_user_by_username(user.username)
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": str(db_user["_id"]), "role": db_user["role"]})
    return {"access_token": token, "token_type": "bearer"}

@router.delete("/staff/{user_id}")
async def remove_staff_member(
    user_id: str,
    current_user: dict = Depends(require_roles("admin"))
):
    """Admin-only. Deletes a Doctor or Admin account."""
    if user_id == current_user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account while logged in as it")
    deleted = await delete_staff(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return {"message": "Staff account deleted successfully"}

@router.put("/staff/{user_id}", response_model=UserOut)
async def edit_staff_member(
    user_id: str,
    update: StaffUpdate,
    current_user: dict = Depends(require_roles("admin"))
):
    """Admin-only. Edits a Doctor/Admin's email and/or role. Username and
    password are intentionally not editable here."""
    updated = await update_staff(user_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return updated