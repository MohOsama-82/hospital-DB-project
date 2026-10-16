import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET")

 # SMTP - used for the patient welcome email (username/password) and the
    # appointment confirmation email. All optional: if SMTP_HOST is unset,
    # the email service silently skips sending (logs a note) instead of
    # crashing the request that triggered it - a stuck mail server should
    # never block someone from being created or an appointment from being
    # accepted.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() != "false"
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "") or os.getenv("SMTP_USERNAME", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Wardline Hospital")
    
settings = Settings()