from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailService:
    def _assert_configured(self) -> None:
        if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
            raise RuntimeError("邮件服务未配置，请先在 .env 配置 SMTP_HOST/SMTP_USER/SMTP_PASSWORD")

    def send_verification_code(self, *, to_email: str, code: str, purpose: str) -> None:
        self._assert_configured()
        title_suffix = "注册验证" if purpose == "register" else "重置密码"
        message = EmailMessage()
        message["Subject"] = f"病虫害检测系统 - {title_suffix}验证码"
        message["From"] = settings.smtp_from_email or settings.smtp_user
        message["To"] = to_email
        message.set_content(
            f"您的验证码是：{code}\n"
            f"用途：{title_suffix}\n"
            f"有效期：{settings.email_code_expire_minutes} 分钟\n"
            "请勿将验证码泄露给他人。"
        )

        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
            return

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


email_service = EmailService()
