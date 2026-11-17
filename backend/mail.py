import json
import os
import smtplib
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
import config


def send_email(to, subject, html):
    if config.MAIL_SERVER == "":
        # no mail server set up, so just save the mail as a file (good for demo)
        filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".html"
        with open(os.path.join(config.OUTBOX_DIR, filename), "w", encoding="utf-8") as f:
            f.write("<p>To: " + to + "<br>Subject: " + subject + "</p><hr>" + html)
        print("Email saved in outbox:", subject, "->", to)
        return
    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = config.MAIL_FROM
    msg["To"] = to
    server = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT)
    server.starttls()
    if config.MAIL_USER:
        server.login(config.MAIL_USER, config.MAIL_PASSWORD)
    server.send_message(msg)
    server.quit()


def send_gchat(text):
    if config.GCHAT_WEBHOOK == "":
        return
    data = json.dumps({"text": text}).encode()
    req = urllib.request.Request(config.GCHAT_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Google chat failed:", e)
