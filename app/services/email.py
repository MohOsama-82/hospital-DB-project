"""
Outbound email - patient welcome (username/password) and appointment
confirmation. Uses smtplib directly (no extra dependency) against whatever
SMTP server is configured in .env (Gmail, SendGrid SMTP relay, your
hospital's own mail server, etc. all work the same way here).

Every send is wrapped so a broken/unconfigured mail server can never take
down the request that triggered it - patient creation and appointment
acceptance both still succeed even if the email fails; the failure is only
logged. Callers should fire these via FastAPI's BackgroundTasks so the
person doesn't sit waiting on an SMTP round-trip before getting their
response.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger("wardline.email")


def _send(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured (SMTP_HOST unset) - skipping email to %s: %s", to_email, subject)
        return
    if not to_email:
        logger.info("No recipient email on record - skipping: %s", subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        logger.info("Email sent to %s: %s", to_email, subject)
    except Exception:
        # Deliberately swallowed - see module docstring. The caller's main
        # operation (account creation / appointment acceptance) already
        # succeeded in the database by the time this runs.
        logger.exception("Failed to send email to %s: %s", to_email, subject)


def _wrap_html(inner_html: str) -> str:
    return f"""\
<div style="font-family:'IBM Plex Sans',Arial,sans-serif;max-width:480px;margin:0 auto;color:#12262b;">
  <div style="background:#084f4c;padding:20px 26px;border-radius:10px 10px 0 0;">
    <span style="color:#fff;font-family:Georgia,serif;font-size:20px;font-weight:600;">Wardline</span>
  </div>
  <div style="border:1px solid #dbe5e5;border-top:none;border-radius:0 0 10px 10px;padding:26px;">
    {inner_html}
  </div>
  <p style="color:#8a9a9d;font-size:11.5px;margin-top:18px;">This is an automated message from Wardline Hospital - please do not reply to this email.</p>
</div>"""


def send_patient_welcome_email(*, to_email: str, patient_name: str, username: str, password: str) -> None:
    """Sent once, right after Admin/Doctor creates a patient account - gives
    them their login so they can sign in and see their own record."""
    subject = "Your Wardline patient account has been created"
    inner = f"""\
    <p>Hi {patient_name},</p>
    <p>A patient account has been created for you at Wardline Hospital. You can sign in any time to view your records and files.</p>
    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:8px 0;color:#4c6268;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;">Username</td><td style="padding:8px 0;font-family:monospace;font-size:15px;font-weight:600;">{username}</td></tr>
      <tr><td style="padding:8px 0;color:#4c6268;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;">Password</td><td style="padding:8px 0;font-family:monospace;font-size:15px;font-weight:600;">{password}</td></tr>
    </table>
    <p>For your security, we recommend signing in and, if your care team offers a way to do so, changing your password after your first login.</p>
    """
    html_body = _wrap_html(inner)
    text_body = (
        f"Hi {patient_name},\n\n"
        f"A patient account has been created for you at Wardline Hospital.\n\n"
        f"Username: {username}\n"
        f"Password: {password}\n\n"
        f"Sign in any time to view your records and files."
    )
    _send(to_email, subject, html_body, text_body)


def send_appointment_confirmation_email(
    *, to_email: str, patient_name: str, doctor_username: str,
    appointment_date: str, appointment_time: str, token_number: int,
) -> None:
    """Sent once, right after the Doctor accepts a pending booking."""
    subject = "Your Wardline appointment is confirmed"
    inner = f"""\
    <p>Hi {patient_name},</p>
    <p>Your appointment has been confirmed by Dr. {doctor_username}.</p>
    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:8px 0;color:#4c6268;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;">Date</td><td style="padding:8px 0;font-size:15px;font-weight:600;">{appointment_date}</td></tr>
      <tr><td style="padding:8px 0;color:#4c6268;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;">Time</td><td style="padding:8px 0;font-size:15px;font-weight:600;">{appointment_time}</td></tr>
      <tr><td style="padding:8px 0;color:#4c6268;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;">Token number</td><td style="padding:8px 0;font-size:15px;font-weight:600;">#{token_number}</td></tr>
    </table>
    <p>This time slot is shared with other patients - you'll be seen in token order, not necessarily exactly at {appointment_time}.</p>
    """
    html_body = _wrap_html(inner)
    text_body = (
        f"Hi {patient_name},\n\n"
        f"Your appointment has been confirmed by Dr. {doctor_username}.\n\n"
        f"Date: {appointment_date}\n"
        f"Time: {appointment_time}\n"
        f"Token number: #{token_number}\n\n"
        f"This time slot is shared with other patients - you'll be seen in token order, "
        f"not necessarily exactly at {appointment_time}."
    )
    _send(to_email, subject, html_body, text_body)