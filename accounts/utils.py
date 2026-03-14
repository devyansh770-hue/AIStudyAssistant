from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(email, otp_code, purpose='verification'):
    if purpose == 'verification':
        subject = 'StudyAI — Verify Your Email'
        message = f"""
Hi there!

Your StudyAI email verification code is:

    {otp_code}

This code expires in 10 minutes.
Do NOT share this with anyone.

If you didn't register on StudyAI, ignore this email.

— StudyAI Team
        """
    else:
        subject = 'StudyAI — Password Reset OTP'
        message = f"""
Hi there!

Your password reset OTP is:

    {otp_code}

This code expires in 15 minutes.
Do NOT share this with anyone.

If you didn't request this, ignore this email.

— StudyAI Team
        """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )