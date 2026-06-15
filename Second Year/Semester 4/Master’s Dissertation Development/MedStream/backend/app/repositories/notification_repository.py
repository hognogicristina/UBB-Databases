import asyncio
import logging
import threading
from email.message import EmailMessage
from urllib.parse import urlencode

import aiosmtplib

from app.core.config import settings
from app.validators.notification_validators import (
    validate_notification_body,
    validate_notification_recipient,
    validate_notification_subject,
    validate_smtp_host,
)

logger = logging.getLogger(__name__)
LOCAL_SMTP_HOSTS = {"localhost", "127.0.0.1", "mailcatcher", "mailhog", "mailpit"}


def _build_frontend_link(path: str, token: str):
    query = urlencode({"token": token})
    return f"{settings.frontend_base_url.rstrip('/')}{path}?{query}"


def build_verify_email_link(token: str):
    return _build_frontend_link("/verify-email", token)


def build_password_reset_link(token: str):
    return _build_frontend_link("/reset-password", token)


def build_account_recovery_link(token: str):
    return _build_frontend_link("/recover-account/verify", token)


def _render_html_email(title: str, message: str, action_label: str, action_url: str):
    return f"""\
<!doctype html>
<html lang=\"en\">
  <body style=\"margin:0;padding:0;background:#f7f8fa;font-family:Segoe UI,Helvetica Neue,Arial,sans-serif;color:#232f3e;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"padding:32px 16px;background:#f7f8fa;\">
      <tr>
        <td align=\"center\">
          <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:600px;border:1px solid #d5dbdb;background:#ffffff;border-radius:8px;overflow:hidden;\">
            <tr>
              <td style=\"height:4px;background:#ff9900;font-size:0;line-height:0;\">&nbsp;</td>
            </tr>
            <tr>
              <td style=\"padding:32px;\">
                <p style=\"margin:0 0 12px;font-size:12px;letter-spacing:0.16em;text-transform:uppercase;color:#5f6b7a;font-weight:700;\">MedStream</p>
                <h1 style=\"margin:0 0 16px;font-size:26px;line-height:1.2;color:#232f3e;\">{title}</h1>
                <p style=\"margin:0 0 24px;font-size:15px;line-height:1.6;color:#5f6b7a;\">{message}</p>
                <a href=\"{action_url}\" style=\"display:inline-block;padding:10px 18px;border-radius:8px;background:#0972d3;color:#ffffff;text-decoration:none;font-weight:700;\">
                  {action_label}
                </a>
                <p style=\"margin:24px 0 8px;font-size:13px;color:#5f6b7a;\">If the button does not work, use this link:</p>
                <p style=\"margin:0;font-size:13px;line-height:1.6;word-break:break-all;\">
                  <a href=\"{action_url}\" style=\"color:#0972d3;text-decoration:none;\">{action_url}</a>
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


async def send_email_async(recipient: str, subject: str, text_body: str, html_body: str):
    email = EmailMessage()
    email["From"] = settings.smtp_user or "no-reply@medstream.local"
    email["To"] = validate_notification_recipient(recipient)
    email["Subject"] = validate_notification_subject(subject)
    email.set_content(validate_notification_body(text_body, "Text body"))
    email.add_alternative(validate_notification_body(html_body, "HTML body"), subtype="html")

    smtp_host = validate_smtp_host(settings.smtp_host)
    logger.info(
        "Sending email to %s via SMTP %s:%s.",
        recipient,
        smtp_host,
        settings.smtp_port,
    )
    await aiosmtplib.send(
        email,
        hostname=smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_pass or None,
        start_tls=settings.smtp_port not in (465, 1025),
        use_tls=settings.smtp_port == 465,
    )
    logger.info("Email accepted by SMTP server for %s.", recipient)
    print(f"Email accepted by SMTP server for {recipient}", flush=True)


def send_email(recipient: str, subject: str, text_body: str, html_body: str):
    validate_smtp_host(settings.smtp_host)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(send_email_async(recipient, subject, text_body, html_body))
        return

    result: dict[str, BaseException | None] = {"error": None}

    def send_in_thread():
        try:
            asyncio.run(send_email_async(recipient, subject, text_body, html_body))
        except BaseException as error:
            result["error"] = error

    thread = threading.Thread(target=send_in_thread, daemon=True)
    thread.start()
    thread.join()

    if result["error"] is not None:
        raise result["error"]


def _log_local_action_link(action_label: str, action_url: str):
    if settings.smtp_host.strip().lower() in LOCAL_SMTP_HOSTS:
        logger.info("%s link: %s", action_label, action_url)
        print(f"{action_label} link: {action_url}", flush=True)


def send_registration_verification_email(email: str, first_name: str, token: str):
    action_url = build_verify_email_link(token)
    _log_local_action_link("Registration verification", action_url)
    print(f"Sending registration verification email to {email} via {settings.smtp_host}:{settings.smtp_port}", flush=True)
    message = f"Hello Dr. {first_name}, your MedStream account is ready. Validate your email address to complete registration."
    send_email(
        email,
        "Validate your MedStream email",
        f"{message}\n\nValidate Email: {action_url}",
        _render_html_email("Validate Your Email", message, "Validate Email", action_url),
    )


def send_password_reset_email(email: str, first_name: str, token: str):
    action_url = build_password_reset_link(token)
    _log_local_action_link("Password reset", action_url)
    print(f"Sending password reset email to {email} via {settings.smtp_host}:{settings.smtp_port}", flush=True)
    message = f"Hello Dr. {first_name}, we received a request to reset your MedStream password. This link expires shortly."
    send_email(
        email,
        "Reset your MedStream password",
        f"{message}\n\nReset Password: {action_url}",
        _render_html_email("Reset Your Password", message, "Reset Password", action_url),
    )


def send_email_change_verification_email(email: str, first_name: str, token: str):
    action_url = build_verify_email_link(token)
    _log_local_action_link("Email change verification", action_url)
    print(f"Sending email change verification email to {email} via {settings.smtp_host}:{settings.smtp_port}", flush=True)
    message = f"Hello Dr. {first_name}, confirm your new email address to finish updating your MedStream account."
    send_email(
        email,
        "Confirm your MedStream email change",
        f"{message}\n\nVerify Email: {action_url}",
        _render_html_email("Confirm Email Change", message, "Verify Email", action_url),
    )


def send_account_recovery_email(email: str, first_name: str, token: str):
    action_url = build_account_recovery_link(token)
    _log_local_action_link("Account recovery", action_url)
    print(f"Sending account recovery email to {email} via {settings.smtp_host}:{settings.smtp_port}", flush=True)
    message = (
        f"Hello Dr. {first_name}, we received a request to recover access to your MedStream account. "
        "Use this secure link to continue to login."
    )
    send_email(
        email,
        "Recover your MedStream account",
        f"{message}\n\nRecover Account: {action_url}",
        _render_html_email("Recover Your Account", message, "Recover Account", action_url),
    )
