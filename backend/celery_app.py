"""
Start the worker:    celery -A celery_app.celery worker --loglevel=info
Start the scheduler: celery -A celery_app.celery beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab
import config
import jobs

celery = Celery("trekison", broker=config.CELERY_BROKER, backend=config.CELERY_BACKEND)
celery.conf.broker_connection_timeout = 2

# scheduled jobs
celery.conf.beat_schedule = {
    "daily-reminders": {
        "task": "trekison.send_daily_reminders",
        "schedule": crontab(hour=8, minute=0),                  # every day at 8:00 AM
    },
    "monthly-report": {
        "task": "trekison.send_monthly_report",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),  # 1st of every month, 6:00 AM
    },
}


@celery.task(name="trekison.send_daily_reminders")
def send_daily_reminders():
    return jobs.send_daily_reminders()


@celery.task(name="trekison.send_monthly_report")
def send_monthly_report():
    return jobs.send_monthly_report()


@celery.task(name="trekison.export_booking_history")
def export_booking_history(export_id):
    return jobs.export_booking_history(export_id)
