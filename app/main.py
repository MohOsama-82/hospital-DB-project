from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, patients, files, appointments

app = FastAPI(title="Hospital API (MongoDB)", version="1.0.0")

# Allows the browser-based GUI (opened as a local file, or served from any
# origin) to call this API. Since this is an internal admin tool with its own
# JWT auth on every route, allowing all origins here is fine; tighten
# allow_origins to your real frontend's URL if you ever deploy this publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No need for Base.metadata.create_all anymore. MongoDB is schemaless.

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")

@app.on_event("startup")
async def startup_db_client():
    from app.database.connection import test_connection, client
    connected = await test_connection()
    if not connected:
        print("⚠️  Warning: Could not connect to MongoDB")
    else:
        # Create indexes if needed
        await create_indexes()

@app.on_event("shutdown")
async def shutdown_db_client():
    from app.database.connection import client
    client.close()

@app.get("/api/health")
def health():
    return {"message": "Hospital API is running with MongoDB"}


async def create_indexes():
    from pymongo.errors import OperationFailure
    from app.database.connection import (
        users_collection, patients_collection, patient_files_collection,
        appointments_collection, slot_counters_collection,
    )

    # Users collection indexes
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("username", unique=True)

    # Patients collection indexes
    await patients_collection.create_index("email", unique=True)
    await patients_collection.create_index("contact")

    # Patient files collection index (metadata only - actual files live in Cloudinary)
    await patient_files_collection.create_index("patient_id")

    # Appointments: a doctor/date/time slot is now a QUEUE, not a single seat -
    # many patients can book the same slot and get sequential token numbers
    # (see slot_counters below), so this is a lookup index only, NOT unique.
    # Older deployments may still have the previous version of this index as
    # unique, which would reject every second booking in a slot - drop it
    # first if present, then (re)create it as a plain, non-unique index.
    try:
        await appointments_collection.drop_index(
            "doctor_id_1_appointment_date_1_appointment_time_1"
        )
    except OperationFailure:
        pass  # didn't exist (fresh DB) or already non-unique - fine either way
    await appointments_collection.create_index(
        [("doctor_id", 1), ("appointment_date", 1), ("appointment_time", 1)]
    )
    await appointments_collection.create_index("appointment_date")

    # Slot counters: one doc per doctor/date/time, $inc'd atomically to hand
    # out each patient's queue position (token_number) for that slot.
    await slot_counters_collection.create_index("_id")

    print("✅ Indexes created/verified")


# Serves the GUI (static/index.html + any assets) at the root URL.
# Registered LAST and deliberately after every /api/... route above, so that
# FastAPI matches those specific routes first - this catch-all only handles
# whatever is left, i.e. the dashboard itself.
app.mount("/", StaticFiles(directory="wardline", html=True), name="waedline")