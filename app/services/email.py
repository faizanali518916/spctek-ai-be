"""Email service for sending reinstatement reports via email."""

import smtplib
import logging
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from app.config import get_settings

logger = logging.getLogger(__name__)


def send_reinstatement_report_email(
    recipient_email: str,
    recipient_name: str,
    pdf_file_path: str,
) -> bool:
    """
    Send the reinstatement report PDF via email.

    Args:
        recipient_email: Email address to send to
        recipient_name: Name of the recipient
        pdf_file_path: Path to the PDF file to attach

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        settings = get_settings()

        # Validate email configuration
        if not all([settings.SMTP_USER, settings.SMTP_PASS, settings.SMTP_HOST]):
            logger.error("Email configuration incomplete - missing SMTP credentials")
            logger.error(
                f"SMTP_USER: {bool(settings.SMTP_USER)}, SMTP_PASS: {bool(settings.SMTP_PASS)}, SMTP_HOST: {bool(settings.SMTP_HOST)}"
            )
            return False

        # Check if PDF file exists
        pdf_path = Path(pdf_file_path)
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_file_path}")
            return False

        # Create email message
        msg = MIMEMultipart()
        msg["From"] = f"{settings.FROM_NAME} <{settings.SMTP_USER}>"
        msg["To"] = recipient_email
        msg["Subject"] = "Your Amazon Seller Reinstatement Report from SPCTEK AI"

        # Email body
        body = f"""Dear {recipient_name},

Thank you for using SPCTEK AI's Amazon Seller Reinstatement Estimator.

Attached is your comprehensive reinstatement assessment report. This report includes:
- Root cause analysis of your account suspension
- Document checklist for reinstatement
- Reinstatement success probability estimates
- Actionable steps for account recovery

Please review the report carefully and follow the recommended steps for the best chance of reinstatement.

If you have any questions, feel free to reach out to our team.

Best regards,
SPCTEK AI Team
"""

        msg.attach(MIMEText(body, "plain"))

        # Attach PDF file
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {pdf_path.name}",
        )
        msg.attach(part)

        # Send email
        logger.info(f"Sending reinstatement report to {recipient_email}")
        logger.info(f"Using SMTP host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")

        # Use SMTP_SSL for port 465, SMTP + STARTTLS for port 587
        if settings.SMTP_PORT == 465:
            logger.info("Using SMTP_SSL (port 465)")
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                logger.info(f"Logging in with user: {settings.SMTP_USER}")
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                logger.info("Login successful, sending message")
                server.send_message(msg)
                logger.info("Message sent successfully")
        else:
            logger.info(f"Using SMTP with STARTTLS (port {settings.SMTP_PORT})")
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                logger.info("Connected to SMTP server, initiating TLS")
                server.starttls()
                logger.info(f"Logging in with user: {settings.SMTP_USER}")
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                logger.info("Login successful, sending message")
                server.send_message(msg)
                logger.info("Message sent successfully")

        logger.info(f"Report successfully sent to {recipient_email}")
        return True

    except Exception as e:
        logger.error(
            f"Failed to send email to {recipient_email}: {str(e)}", exc_info=True
        )
        return False
