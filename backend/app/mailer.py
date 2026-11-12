"""SMTP delivery with fixed operator configuration and no request-derived headers."""
import os
import re
import smtplib
import ssl
from email.message import EmailMessage


class MailUnavailable(Exception):
    pass


def _email(value):
    # No display names or control characters in configurable SMTP addresses.
    return bool(re.fullmatch(r'[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+', value or ''))


def configuration():
    host = os.getenv('SMTP_HOST', '').strip()
    sender = os.getenv('SMTP_FROM', '').strip()
    security = os.getenv('SMTP_SECURITY', 'starttls').strip().lower()
    username = os.getenv('SMTP_USERNAME', '')
    password = os.getenv('SMTP_PASSWORD', '')
    try:
        port = int(os.getenv('SMTP_PORT', '465' if security == 'ssl' else '587'))
    except ValueError:
        port = 0
    if (not host or re.search(r'[\s\r\n]', host) or not _email(sender)
            or security not in {'starttls', 'ssl'} or not 1 <= port <= 65535
            or bool(username) != bool(password)):
        raise MailUnavailable('Password recovery email is not configured.')
    return host, port, sender, security, username, password


def is_configured():
    try:
        configuration()
        return True
    except MailUnavailable:
        return False


def _send_message(recipient, subject, body):
    if not _email(recipient):
        raise MailUnavailable('Invalid recipient.')
    host, port, sender, security, username, password = configuration()
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = 'Candoc <' + sender + '>'
    message['To'] = recipient
    message.set_content(body)
    context = ssl.create_default_context()
    try:
        connection = (smtplib.SMTP_SSL(host, port, timeout=12, context=context)
                      if security == 'ssl' else smtplib.SMTP(host, port, timeout=12))
        with connection as client:
            if security == 'starttls':
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            if username:
                client.login(username, password)
            refused = client.send_message(message)
            if refused:
                raise MailUnavailable('Email delivery is temporarily unavailable.')
    except (smtplib.SMTPException, OSError, ValueError):
        # Provider response text can contain addresses/credentials; never propagate it.
        raise MailUnavailable('Email delivery is temporarily unavailable.') from None


def send_password_reset(recipient, reset_url):
    _send_message(recipient, 'Reset your Candoc password',
                  'A password reset was requested for this email address on Candoc.\n\n'
                  'If you have a Candoc account, use this link within 20 minutes:\n'
                  + reset_url + '\n\n'
                  'This link works once. Your password and active sessions change only after you choose a new password.\n'
                  'If you did not request this, ignore this email. Never share the link or your password.\n')


def send_password_changed(recipient):
    _send_message(recipient, 'Your Candoc password was changed',
                  'Your Candoc password was changed successfully. All previous sessions have been signed out.\n\n'
                  'If you made this change, no action is needed.\n'
                  'If you did not make this change, use Forgot password on the Candoc sign-in page '
                  'to secure your account and contact the site operator.\n'
                  'Never share your password or password reset links.\n')
