"""Email service for BinderPro transactional emails."""

import logging
from typing import Optional

import resend

from app.config import settings

logger = logging.getLogger("home_binder.email")

# Brand colors and styles
BRAND_COLOR = "#059669"  # emerald-600
BRAND_NAME = "BinderPro"


def _base_template(content: str, preheader: str = "") -> str:
    """Wrap content in base email template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{BRAND_NAME}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #374151; margin: 0; padding: 0; background-color: #f3f4f6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 24px; }}
        .logo {{ font-size: 24px; font-weight: bold; color: {BRAND_COLOR}; text-decoration: none; }}
        .content {{ margin-bottom: 24px; }}
        .button {{ display: inline-block; background: {BRAND_COLOR}; color: white !important; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; }}
        .button:hover {{ background: #047857; }}
        .footer {{ text-align: center; color: #9ca3af; font-size: 14px; margin-top: 24px; }}
        .code {{ font-size: 32px; font-weight: bold; letter-spacing: 4px; color: {BRAND_COLOR}; text-align: center; padding: 16px; background: #f3f4f6; border-radius: 8px; margin: 16px 0; }}
        h1 {{ color: #111827; margin: 0 0 16px 0; font-size: 24px; }}
        p {{ margin: 0 0 16px 0; }}
        .preheader {{ display: none !important; visibility: hidden; opacity: 0; color: transparent; height: 0; width: 0; }}
    </style>
</head>
<body>
    <span class="preheader">{preheader}</span>
    <div class="container">
        <div class="card">
            <div class="header">
                <a href="{settings.frontend_url}" class="logo">{BRAND_NAME}</a>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p>&copy; {BRAND_NAME}. Your home, organized.</p>
                <p style="margin-top: 8px; font-size: 12px;">
                    You're receiving this because you have a {BRAND_NAME} account.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""


def _send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success."""
    if not settings.resend_api_key:
        logger.warning("No Resend API key configured, skipping email to %s", to)
        return False

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_otp_email(to: str, code: str) -> bool:
    """Send OTP verification code."""
    content = f"""
        <h1>Your verification code</h1>
        <p>Enter this code to sign in to your BinderPro account:</p>
        <div class="code">{code}</div>
        <p>This code expires in 10 minutes.</p>
        <p style="color: #9ca3af; font-size: 14px;">If you didn't request this code, you can safely ignore this email.</p>
    """
    html = _base_template(content, f"Your verification code is {code}")
    return _send_email(to, f"Your BinderPro code: {code}", html)


def send_welcome_email(to: str) -> bool:
    """Send welcome email after first signup."""
    content = f"""
        <h1>Welcome to BinderPro!</h1>
        <p>Thanks for creating your account. You're on your way to having a personalized home operating manual.</p>
        <p>Here's what happens next:</p>
        <ol style="margin: 16px 0; padding-left: 24px;">
            <li><strong>Complete your home assessment</strong> — Tell us about your home, features, and preferences</li>
            <li><strong>Choose your plan</strong> — Select Standard or In-Depth based on your needs</li>
            <li><strong>Get your binder</strong> — We'll generate a personalized PDF you can print or share</li>
        </ol>
        <p style="text-align: center; margin-top: 24px;">
            <a href="{settings.frontend_url}/onboarding" class="button">Start Your Assessment</a>
        </p>
    """
    html = _base_template(content, "Welcome! Let's get your home organized.")
    return _send_email(to, "Welcome to BinderPro!", html)


def send_payment_confirmation(
    to: str,
    tier: str,
    amount_cents: int,
    receipt_url: Optional[str] = None
) -> bool:
    """Send payment confirmation receipt."""
    amount = f"${amount_cents / 100:.2f}"
    plan_name = "In-Depth Binder" if tier == "premium" else "Standard Binder"

    receipt_link = ""
    if receipt_url:
        receipt_link = f'<p><a href="{receipt_url}" style="color: {BRAND_COLOR};">View receipt on Stripe</a></p>'

    content = f"""
        <h1>Payment Confirmed</h1>
        <p>Thank you for your purchase! Here are the details:</p>
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 0;"><strong>Plan:</strong> {plan_name}</p>
            <p style="margin: 8px 0 0 0;"><strong>Amount:</strong> {amount}</p>
        </div>
        {receipt_link}
        <p>Your binder is now being generated. We'll send you another email when it's ready to download.</p>
        <p style="text-align: center; margin-top: 24px;">
            <a href="{settings.frontend_url}/dashboard" class="button">Go to Dashboard</a>
        </p>
    """
    html = _base_template(content, f"Payment confirmed: {plan_name} - {amount}")
    return _send_email(to, f"BinderPro Payment Confirmed - {amount}", html)


def send_binder_ready(to: str, tier: str) -> bool:
    """Send notification when binder PDF is ready."""
    plan_name = "In-Depth Binder" if tier == "premium" else "Standard Binder"

    content = f"""
        <h1>Your Binder is Ready!</h1>
        <p>Great news! Your {plan_name} has been generated and is ready to download.</p>
        <p>Your binder includes:</p>
        <ul style="margin: 16px 0; padding-left: 24px;">
            <li>Emergency quick-start cards</li>
            <li>Personalized emergency playbooks</li>
            <li>Maintenance schedules and checklists</li>
            <li>All your contacts and vendor information</li>
            {"<li>Detailed system guides (premium)</li>" if tier == "premium" else ""}
        </ul>
        <p style="text-align: center; margin-top: 24px;">
            <a href="{settings.frontend_url}/dashboard" class="button">Download Your Binder</a>
        </p>
        <p style="color: #9ca3af; font-size: 14px; margin-top: 24px;">
            Tip: Print your binder and keep it somewhere accessible for emergencies!
        </p>
    """
    html = _base_template(content, f"Your {plan_name} is ready to download!")
    return _send_email(to, "Your BinderPro is Ready!", html)


def send_generation_failed(to: str, tier: str) -> bool:
    """Send notification if binder generation failed."""
    plan_name = "In-Depth Binder" if tier == "premium" else "Standard Binder"

    content = f"""
        <h1>Binder Generation Issue</h1>
        <p>We encountered a problem generating your {plan_name}. Don't worry — you haven't been charged again, and you can retry from your dashboard.</p>
        <p style="text-align: center; margin: 24px 0;">
            <a href="{settings.frontend_url}/dashboard" class="button">Retry Generation</a>
        </p>
        <p style="color: #9ca3af; font-size: 14px;">
            If the problem persists, please contact support.
        </p>
    """
    html = _base_template(content, "There was an issue generating your binder")
    return _send_email(to, "BinderPro Generation Issue", html)


def send_order_message(to: str, message_preview: str) -> bool:
    """Send notification when admin sends an order message."""
    content = f"""
        <h1>Message from the BinderPro Team</h1>
        <p>You have a new message regarding your BinderPro order:</p>
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 0; color: #374151;">{message_preview}</p>
        </div>
        <p>Please log in to your dashboard to view the full message and reply.</p>
        <p style="text-align: center; margin-top: 24px;">
            <a href="{settings.frontend_url}/dashboard" class="button">View Message</a>
        </p>
    """
    html = _base_template(content, "You have a new message about your BinderPro order")
    return _send_email(to, "Message from BinderPro Team", html)


def send_order_shipped(to: str, tracking_number: str, tier: str) -> bool:
    """Send notification when order has shipped."""
    plan_name = "In-Depth Binder" if tier == "premium" else "Standard Binder"

    tracking_info = ""
    if tracking_number:
        tracking_info = f"""
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 0;"><strong>Tracking Number:</strong></p>
            <p style="margin: 8px 0 0 0; font-family: monospace; font-size: 16px;">{tracking_number}</p>
        </div>
        """

    content = f"""
        <h1>Your Binder Has Shipped!</h1>
        <p>Great news! Your {plan_name} is on its way to you.</p>
        {tracking_info}
        <p>Your printed binder includes everything from your digital version, professionally printed and bound for easy reference during emergencies.</p>
        <p><strong>What to do when it arrives:</strong></p>
        <ul style="margin: 16px 0; padding-left: 24px;">
            <li>Keep it in an accessible location (kitchen, entryway, or home office)</li>
            <li>Share its location with household members</li>
            <li>Review the emergency quick-start cards first</li>
        </ul>
        <p style="text-align: center; margin-top: 24px;">
            <a href="{settings.frontend_url}/dashboard" class="button">View Digital Copy</a>
        </p>
        <p style="color: #9ca3af; font-size: 14px; margin-top: 24px;">
            Thank you for choosing BinderPro!
        </p>
    """
    html = _base_template(content, f"Your {plan_name} has shipped!")
    return _send_email(to, "Your BinderPro Has Shipped!", html)
