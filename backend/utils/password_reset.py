"""
Password-reset tokens and reset e-mail delivery.

Security properties (see tests/test_password_reset_security.py):
- The raw token exists only in the e-mail sent to the account's registered address.
  The database stores its SHA-256 hash; API responses, pages and logs never contain it.
- Tokens are random (256 bits), expire after RESET_TOKEN_TTL, and are single-use: they
  are consumed with one conditional UPDATE, so two concurrent requests cannot both use one.
- Requesting a new link, or a successful reset, invalidates every other outstanding link.
"""
import hashlib
import hmac
import logging
import os
import secrets
import smtplib
import threading
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

log = logging.getLogger(__name__)

RESET_TOKEN_TTL = timedelta(hours=1)
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def is_production() -> bool:
    return os.environ.get('SKILLBRIDGE_ENV', '').lower() == 'production'


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def new_token() -> tuple[str, str]:
    """Returns (raw token for the e-mail, hash to store)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def password_problem(new_password, confirm_password):
    """Returns an error message, or None if the new password is acceptable."""
    if not isinstance(new_password, str) or not isinstance(confirm_password, str) \
            or not new_password or not confirm_password:
        return 'New password and confirmation are required'
    if len(new_password) < PASSWORD_MIN_LENGTH:
        return f'Password must be at least {PASSWORD_MIN_LENGTH} characters long'
    if len(new_password) > PASSWORD_MAX_LENGTH:
        return f'Password must be at most {PASSWORD_MAX_LENGTH} characters long'
    if not hmac.compare_digest(new_password.encode('utf-8'), confirm_password.encode('utf-8')):
        return 'Passwords do not match'
    return None


def mask_email(email: str) -> str:
    """a.student@example.com -> a*******@example.com (shown on the reset page)."""
    local, _, domain = (email or '').partition('@')
    if not domain:
        return ''
    return f"{local[:1]}{'*' * max(len(local) - 1, 3)}@{domain}"


def reset_link(raw_token: str) -> str:
    # The token goes in the URL fragment (#...): browsers never send fragments to servers
    # or in Referer headers, so it cannot end up in proxy/web-server access logs.
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
    return f"{frontend_url}/reset-password#token={raw_token}"


# ---------------------------------------------------------------- e-mail

def mail_settings() -> dict:
    return {
        'server': (os.environ.get('MAIL_SERVER') or '').strip(),
        'port': int(os.environ.get('MAIL_PORT') or 587),
        'username': (os.environ.get('MAIL_USERNAME') or '').strip(),
        'password': (os.environ.get('MAIL_PASSWORD') or '').strip(),
        'use_tls': (os.environ.get('MAIL_USE_TLS') or 'true').lower() in ('true', '1', 'yes'),
        'use_ssl': (os.environ.get('MAIL_USE_SSL') or 'false').lower() in ('true', '1', 'yes'),
        'sender': (os.environ.get('MAIL_FROM') or os.environ.get('MAIL_USERNAME') or '').strip(),
    }


def mail_configured() -> bool:
    s = mail_settings()
    return bool(s['server'] and s['username'] and s['password'] and s['sender'])


def send_email(to_email: str, subject: str, text: str, html: str | None = None) -> tuple[bool, str]:
    """Sends one e-mail over SMTP. Never raises; returns (sent, reason)."""
    s = mail_settings()
    if not mail_configured():
        return False, 'Email service is not configured (MAIL_SERVER/MAIL_USERNAME/MAIL_PASSWORD/MAIL_FROM)'
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr(('SkillBridge', s['sender']))
    msg['To'] = to_email
    msg['Message-ID'] = make_msgid(domain=s['sender'].partition('@')[2] or None)
    msg.attach(MIMEText(text, 'plain', 'utf-8'))
    if html:
        msg.attach(MIMEText(html, 'html', 'utf-8'))
    try:
        if s['use_ssl']:
            server = smtplib.SMTP_SSL(s['server'], s['port'], timeout=15)
        else:
            server = smtplib.SMTP(s['server'], s['port'], timeout=15)
        with server:
            if s['use_tls'] and not s['use_ssl']:
                server.starttls()
            server.login(s['username'], s['password'])
            server.send_message(msg)
        return True, 'sent'
    except Exception as e:  # network/auth errors: report, never crash the request
        return False, f'{type(e).__name__}: {e}'


def _reset_email(link: str) -> tuple[str, str]:
    minutes = int(RESET_TOKEN_TTL.total_seconds() // 60)
    text = f"""Hello,

We received a request to reset the password for your SkillBridge account.
Open this link to choose a new password:

{link}

The link works once and expires in {minutes} minutes. If you did not ask for this,
ignore this e-mail: your password stays the same.

The SkillBridge Team
"""
    html = f"""<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; background:#0b0f19; color:#fff; padding:30px;">
  <div style="max-width:540px; margin:0 auto; background:#131b2e; border:1px solid #1e293b; border-radius:16px; padding:32px;">
    <h2 style="color:#2dd4bf; margin-top:0;">SkillBridge</h2>
    <h3 style="color:#f1f5f9;">Reset your password</h3>
    <p style="color:#94a3b8; font-size:14px; line-height:1.6;">We received a request to reset the password for your SkillBridge account.</p>
    <p style="text-align:center; margin:30px 0;">
      <a href="{link}" style="background:#0d9488; color:#fff; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:bold;">Choose a new password</a>
    </p>
    <p style="color:#64748b; font-size:12px;">Or paste this link into your browser:<br><a href="{link}" style="color:#2dd4bf; word-break:break-all;">{link}</a></p>
    <p style="color:#64748b; font-size:11px;">The link works once and expires in {minutes} minutes. If you did not ask for this, ignore this e-mail: your password stays the same.</p>
  </div>
</body></html>"""
    return text, html


def deliver_reset_email(to_email: str, raw_token: str) -> tuple[bool, str]:
    """Sends the reset link to the account's registered address. Logs never contain the link."""
    link = reset_link(raw_token)
    if not mail_configured():
        if is_production():
            log.error('Password reset requested but e-mail is not configured; no link was sent.')
            return False, 'not configured'
        # Local development only: print the link to the server console (never to the browser).
        print('\n[DEVELOPMENT] Email is not configured. Password reset link for '
              f'{to_email}:\n{link}\n', flush=True)
        return False, 'printed to development console'
    text, html = _reset_email(link)
    sent, reason = send_email(to_email, 'Reset your SkillBridge password', text, html)
    if not sent:
        log.error('Password reset e-mail could not be sent: %s', reason)
    return sent, reason


def deliver_in_background(app, to_email: str, raw_token: str) -> None:
    """Sends without holding up the response, so registered and unknown addresses take the
    same time to answer (timing would otherwise reveal which e-mails have accounts)."""
    if app.config.get('TESTING') or app.config.get('MAIL_SEND_SYNC'):
        deliver_reset_email(to_email, raw_token)
        return

    def _run():
        with app.app_context():
            deliver_reset_email(to_email, raw_token)

    threading.Thread(target=_run, name='password-reset-mail', daemon=True).start()


def utc_aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
