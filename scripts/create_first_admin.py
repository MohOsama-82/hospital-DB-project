"""
One-time bootstrap script.

Since /auth/create-staff requires you to already be logged in as an Admin,
there has to be some way to create the very FIRST Admin account. This script
inserts that first Admin directly into MongoDB, bypassing the API.

Run it once, from the project root:

    python -m scripts.create_first_admin

Then log in via POST /api/auth/login with the username/password you set
below, and use that Admin account's token to create Doctors and further
Admins through POST /api/auth/create-staff.

NOTE: This script deliberately creates its own MongoDB client inside main(),
instead of importing the shared client from app.database.connection. If that
shared client is created at import time (before the event loop is running),
Motor can bind it to the wrong event loop on Windows and raise:
  RuntimeError: Task ... got Future ... attached to a different loop
Building the client here, after the loop is already running, avoids that.
"""
import asyncio
import getpass
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.auth.utils import get_password_hash


async def main():
    client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        tlsAllowInvalidCertificates=False,
        tlsCAFile=certifi.where()
    )
    db = client[settings.DATABASE_NAME]
    users_collection = db.get_collection("users")

    try:
        await client.admin.command("ping")
    except Exception as e:
        print(f"❌ Could not connect to MongoDB: {e}")
        return

    print("=== Create the first Admin account ===")
    user_id = input("User ID (manually chosen, e.g. ADM001): ").strip()
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password (min 8 chars): ")

    if len(password) < 8:
        print("❌ Password must be at least 8 characters.")
        return

    existing = await users_collection.find_one(
        {"$or": [{"_id": user_id}, {"username": username}, {"email": email}]}
    )
    if existing:
        print("❌ A user with that user_id, username, or email already exists.")
        return

    user_dict = {
        "_id": user_id,
        "username": username,
        "email": email,
        "hashed_password": get_password_hash(password),
        "role": "admin",
        "is_active": True,
    }
    await users_collection.insert_one(user_dict)
    print(f"✅ Admin created with user_id: {user_id}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())