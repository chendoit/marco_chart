"""Gmail SMTP 寄信（應用程式密碼）。讀取 .env：MAIL_TOKEN、APP_PASSWORD、RECIPIENTS。"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def _parse_recipients(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for part in raw.replace(";", ",").split(","):
        p = part.split("#", 1)[0].strip()
        if p:
            out.append(p)
    return out


def send_html_email_from_env(subject: str, html: str) -> None:
    sender = (os.getenv("MAIL_TOKEN") or "").strip()
    app_pw = (os.getenv("APP_PASSWORD") or "").strip()
    recipients = _parse_recipients(os.getenv("RECIPIENTS"))
    if not sender or not app_pw:
        raise RuntimeError("請在 .env 設定 MAIL_TOKEN（寄件 Gmail）與 APP_PASSWORD（應用程式密碼）")
    if not recipients:
        raise RuntimeError("請在 .env 設定 RECIPIENTS（逗號分隔收件人）")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(sender, app_pw.replace(" ", ""))
        server.send_message(msg)
