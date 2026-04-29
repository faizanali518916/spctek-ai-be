import smtplib
import logging
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from app.config import get_settings

logger = logging.getLogger(__name__)

# Set up Jinja2 environment for templates
template_dir = Path(__file__).parent.parent / "templates"
env = Environment(loader=FileSystemLoader(str(template_dir)))


def render_template(template_name: str, context: dict) -> str:
    """Render HTML template with context data."""
    try:
        template = env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        logger.error(f"Failed to render template {template_name}: {str(e)}", exc_info=True)
        return ""


def send_form_submission_email(
    recipient_email: str,
    recipient_name: str,
    source: str,
    journey_data: dict,
) -> bool:
    """
    Send form submission email with HTML report.

    Args:
        recipient_email: Email address to send to
        recipient_name: Name of the recipient
        source: Form source (process_diagnostic, ai_deployment_roadmap, ai_playbook)
        journey_data: Form data and results

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        settings = get_settings()

        # Validate email configuration
        if not all([settings.SMTP_USER, settings.SMTP_PASS, settings.SMTP_HOST]):
            logger.error("Email configuration incomplete - missing SMTP credentials")
            return False

        # Determine template and subject based on source
        if source == "process_diagnostic":
            template_name = "process_rating_email.html"
            subject = "Your Process Health Scorecard"
            context = {
                "score": journey_data.get("score", 0),
                "category": journey_data.get("category", "N/A"),
                "motive": journey_data.get("motive", "N/A"),
                "teamSize": journey_data.get("teamSize", "N/A"),
                "industry": journey_data.get("industry", "N/A"),
                "sopLocation": journey_data.get("sopLocation", "N/A"),
                "toolIntegration": journey_data.get("toolIntegration", "N/A"),
                "pointers": journey_data.get("pointers", []),
            }
        elif source == "ai_deployment_roadmap":
            template_name = "ai_roadmap_email.html"
            subject = "Your AI Deployment Roadmap"
            recommendation = journey_data.get("recommendation", {})
            tier = recommendation.get("tier", {})
            context = {
                "tier_label": tier.get("label", "Standard"),
                "tier_specs": tier.get("specs", ""),
                "use_cases": ", ".join(journey_data.get("useCases", [])),
                "team_size": journey_data.get("teamSize", "N/A"),
                "data_sensitivity": journey_data.get("dataSensitivity", "N/A"),
                "deployment_model": journey_data.get("deploymentModel", "N/A"),
                "reason": recommendation.get("reason", ""),
                "deployment_note": recommendation.get("deploymentNote", ""),
                "model_groups": recommendation.get("modelGroups", []),
            }
        elif source == "ai_playbook":
            template_name = "ai_playbook_email.html"
            subject = "Your AI Automation Playbook"
            recommendation = journey_data.get("recommendation", {})
            context = {
                "recommendation_title": recommendation.get("title", "Your Recommendation"),
                "business_type": journey_data.get("businessType", "N/A"),
                "revenue_range": journey_data.get("revenueRange", "N/A"),
                "playbook_focus": journey_data.get("playbookFocus", "N/A"),
                "urgency": journey_data.get("urgency", "N/A"),
                "recommendation_message": recommendation.get("message", ""),
                "operational_challenge": journey_data.get("operationalChallenge", ""),
            }
        else:
            logger.error(f"Unknown source: {source}")
            return False

        # Render HTML template
        html_content = render_template(template_name, context)
        if not html_content:
            logger.error("Failed to render HTML template")
            return False

        # Create email message
        msg = MIMEMultipart("alternative")
        msg["To"] = recipient_email
        msg["From"] = f"SPCTEK AI <{settings.SMTP_USER}>"
        msg["Subject"] = subject

        # Plain-text fallback
        text_content = f"Dear {recipient_name},\n\nThank you for using SPCTEK AI. Your report is ready. Please view this email in a client that supports HTML to see your full report."

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Send email
        logger.info(f"Sending form submission email to {recipient_email}")
        logger.info(f"Using SMTP host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")

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

        logger.info(f"Email successfully sent to {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}", exc_info=True)
        return False


def send_contact_thank_you_email(
    recipient_email: str,
    recipient_name: str,
    company: str = "",
    message: str = "",
) -> bool:
    """
    Send thank you email for contact form submissions.

    Args:
        recipient_email: Email address to send to
        recipient_name: Name of the recipient
        company: Company name (optional)
        message: Message from contact form

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        settings = get_settings()

        # Validate email configuration
        if not all([settings.SMTP_USER, settings.SMTP_PASS, settings.SMTP_HOST]):
            logger.error("Email configuration incomplete - missing SMTP credentials")
            return False

        # Render HTML template
        context = {
            "name": recipient_name,
            "company": company,
            "message": message,
        }
        html_content = render_template("contact_thank_you.html", context)
        if not html_content:
            logger.error("Failed to render contact thank you template")
            return False

        # Create email message
        msg = MIMEMultipart("alternative")
        msg["To"] = recipient_email
        msg["From"] = f"SPCTEK AI <{settings.SMTP_USER}>"
        msg["Subject"] = "Thank You for Contacting SPCTEK AI"

        # Plain-text fallback
        text_content = f"Dear {recipient_name},\n\nThank you for contacting SPCTEK AI. We've received your message and will get back to you soon."

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Send email
        logger.info(f"Sending contact thank you email to {recipient_email}")

        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)

        logger.info(f"Contact thank you email successfully sent to {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send contact thank you email to {recipient_email}: {str(e)}", exc_info=True)
        return False


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

        # 1. Create the root message container (multipart/mixed for attachments)
        msg = MIMEMultipart("mixed")
        msg["To"] = recipient_email
        msg["From"] = f"SPCTEK AI <{settings.SMTP_USER}>"
        msg["Subject"] = "Your Amazon Reinstatement Assessment Report"

        # 2. Create the body container (multipart/alternative for Plain + HTML)
        msg_body = MIMEMultipart("alternative")

        # Plain-text version (fallback)
        text_content = f"Dear {recipient_name},\n\nThank you for using SPCTEK AI. Your report is attached."

        # Rich HTML version
        html_content = f"""
        <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
                    <div style="background-color: #606bfa; padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 24px;">Reinstatement Assessment</h1>
                    </div>
                    <div style="padding: 30px; background-color: #ffffff;">
                        <p style="font-size: 16px;">Dear <strong>{recipient_name}</strong>,</p>
                        <p>Thank you for using <strong>SPCTEK AI</strong>. Our analysis of your Amazon Performance Notification is complete.</p>
                        
                        <div style="background-color: #f8f9ff; border-left: 4px solid #606bfa; padding: 15px; margin: 20px 0;">
                            <p style="margin: 0; font-weight: bold; color: #4e59e5;">What's inside your report:</p>
                            <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                                <li>Root Cause Identification</li>
                                <li>Required Documentation Checklist</li>
                                <li>Reinstatement Probability Score</li>
                                <li>Step-by-Step Recovery Action Plan</li>
                            </ul>
                        </div>

                        <p>Please find your comprehensive <strong>PDF report attached</strong> to this email.</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <p style="font-size: 14px; color: #666;">Need professional help with your appeal?</p>
                            <a href="https://spctek-ai-fe.vercel.app/contact" style="background-color: #606bfa; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Speak to an Expert</a>
                        </div>
                    </div>
                    <div style="background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; color: #888;">
                        <p style="margin: 5px 0;">&copy; 2026 SPCTEK AI. All rights reserved.</p>
                        <p style="margin: 5px 0;">This is an automated AI-generated assessment.</p>
                    </div>
                </div>
            </body>
        </html>
        """

        msg_body.attach(MIMEText(text_content, "plain"))
        msg_body.attach(MIMEText(html_content, "html"))

        # Attach the body container to the main message
        msg.attach(msg_body)

        # 3. Attach PDF file
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename=Reinstatement_Report_{recipient_name.replace(' ', '_')}.pdf",
        )
        msg.attach(part)

        # 4. Send email (Same SMTP logic as before)
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
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}", exc_info=True)
        return False
