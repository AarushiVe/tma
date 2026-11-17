import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.environ.get("TREKISON_INSTANCE_DIR", os.path.join(BASE_DIR, "instance"))
DATABASE = os.environ.get("TREKISON_DB", os.path.join(INSTANCE_DIR, "trekison.sqlite3"))
EXPORT_DIR = os.path.join(INSTANCE_DIR, "exports")
REPORT_DIR = os.path.join(INSTANCE_DIR, "reports")
OUTBOX_DIR = os.path.join(INSTANCE_DIR, "outbox")
for folder in (INSTANCE_DIR, EXPORT_DIR, REPORT_DIR, OUTBOX_DIR):
    os.makedirs(folder, exist_ok=True)

SECRET_KEY = "trekison-secret-key"

# the one and only admin (created automatically when the app starts)
ADMIN_EMAIL = "admin@trekison.com"
ADMIN_PASSWORD = "Admin@123"

MAX_PEOPLE = 10          # max people in one booking
STAFF_GAP_DAYS = 2       # a staff member needs 2 free days between two treks
REMINDER_DAYS = 3        # remind users about treks starting in the next 3 days

REDIS_URL = "redis://localhost:6379/0"          # cache
CELERY_BROKER = "redis://localhost:6379/1"      # celery queue
CELERY_BACKEND = "redis://localhost:6379/2"
CACHE_SECONDS = 60

# email settings. If MAIL_SERVER is empty, emails are saved in instance/outbox
MAIL_SERVER = ""
MAIL_PORT = 587
MAIL_USER = ""
MAIL_PASSWORD = ""
MAIL_FROM = "trekison@example.com"
GCHAT_WEBHOOK = ""       # paste a Google Chat webhook url here to get chat reminders
