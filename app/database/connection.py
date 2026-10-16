from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import certifi

# Add SSL/TLS certificate verification for Atlas
client = AsyncIOMotorClient(
    settings.MONGODB_URL,
    tlsAllowInvalidCertificates=False,
    tlsCAFile=certifi.where()
)
database = client[settings.DATABASE_NAME]

# Collections
users_collection = database.get_collection("users")
patients_collection = database.get_collection("patients")

# Actual file bytes now live in Cloudinary, not MongoDB. This collection only
# stores metadata (which Cloudinary asset belongs to which patient, filename,
# content type, etc.) so we can list/authorize access to files per patient.
patient_files_collection = database.get_collection("patient_files")

# Appointment bookings - both guest (no-account) and logged-in-patient bookings
# live here, distinguished by is_guest / patient_id. Multiple patients CAN
# share the same doctor/date/time slot - each gets a queue position
# (token_number) instead of exclusive ownership of the slot.
appointments_collection = database.get_collection("appointments")

# One counter document per (doctor_id, appointment_date, appointment_time)
# slot, e.g. _id = "doc123|2026-08-14|10:00". Incremented atomically to hand
# out the next token number, so two simultaneous bookings never collide.
slot_counters_collection = database.get_collection("slot_counters")

# Helper to get DB
async def get_db():
    return database

# Test connection function
async def test_connection():
    try:
        await client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return False