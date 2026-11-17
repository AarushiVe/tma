"""Small functions used by many routes: login check, notifications, cache, background jobs."""
import json
import threading
from datetime import date
from functools import wraps
from flask import request, g, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import config
from db import query, query_one, execute


def error(message, code=400):
    return jsonify(error=message), code


# ---------------- login token ----------------
serializer = URLSafeTimedSerializer(config.SECRET_KEY)


def make_token(user_id):
    return serializer.dumps(user_id)


def login_required(role=None):
    """Use as @login_required() or @login_required('admin')"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return error("Please login first", 401)
            try:
                user_id = serializer.loads(header[7:], max_age=60 * 60 * 12)
            except (BadSignature, SignatureExpired):
                return error("Session expired, please login again", 401)

            user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
            if user is None:
                return error("User not found", 401)
            if user["status"] != "active":
                return error("Your account is " + user["status"], 403)
            if role is not None and user["role"] != role:
                return error("You are not allowed to do this", 403)
            g.user = user
            return func(*args, **kwargs)
        return wrapper
    return decorator


def notify(user_id, message):
    execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, message))


# ---------------- redis cache ----------------
CACHE_KEY = "trekison_open_treks"
redis_client = None


def cache_get():
    global redis_client
    try:
        if redis_client is None:
            import redis
            redis_client = redis.Redis.from_url(config.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        data = redis_client.get(CACHE_KEY)
        return json.loads(data) if data else None
    except Exception:
        return None      # redis not running, just skip the cache


def cache_set(value):
    try:
        redis_client.setex(CACHE_KEY, config.CACHE_SECONDS, json.dumps(value))
    except Exception:
        pass


def cache_clear():
    """call this whenever a trek or booking changes"""
    try:
        redis_client.delete(CACHE_KEY)
    except Exception:
        pass


# ---------------- treks ----------------
TREK_QUERY = """
SELECT t.*, u.name AS staff_name,
  (SELECT COALESCE(SUM(people), 0) FROM bookings b
     WHERE b.trek_id = t.id AND b.status != 'Cancelled') AS registered,
  (SELECT COUNT(*) FROM bookings b
     WHERE b.trek_id = t.id AND b.status != 'Cancelled') AS booking_count
FROM treks t LEFT JOIN users u ON u.id = t.staff_id
"""


def get_trek(trek_id):
    return query_one(TREK_QUERY + " WHERE t.id = ?", (trek_id,))


def update_finished_treks():
    """treks whose end date is over become Completed (and their bookings too)"""
    today = date.today().isoformat()
    execute("UPDATE treks SET status='Completed' WHERE end_date < ? AND status IN ('Approved','Open','Closed')", (today,))
    execute("UPDATE bookings SET status='Completed' WHERE status='Booked' "
            "AND trek_id IN (SELECT id FROM treks WHERE status='Completed')")


def get_open_treks():
    treks = cache_get()
    if treks is None:
        update_finished_treks()
        treks = query(TREK_QUERY + " WHERE t.status='Open' AND t.start_date > ? ORDER BY t.start_date",
                      (date.today().isoformat(),))
        cache_set(treks)
    return treks


# ---------------- bookings ----------------
BOOKING_QUERY = """
SELECT b.*, t.name AS trek_name, t.location, t.start_date, t.end_date,
       t.status AS trek_status, t.price, u.name AS user_name, u.email AS user_email,
       b.people * t.price AS total_amount
FROM bookings b JOIN treks t ON t.id = b.trek_id JOIN users u ON u.id = b.user_id
"""


def add_participants(bookings):
    for b in bookings:
        b["participants"] = query("SELECT * FROM participants WHERE booking_id=?", (b["id"],))
    return bookings


def cancel_booking(booking):
    """cancel a booking and give the slots back to the trek.
    If the user had already paid, the money is refunded (demo). Returns the refund amount (0 if none)."""
    refund = 0
    new_payment = booking["payment_status"]
    if booking["payment_status"] == "Paid":
        trek = query_one("SELECT price FROM treks WHERE id=?", (booking["trek_id"],))
        refund = booking["people"] * trek["price"]
        new_payment = "Refunded"

    execute("UPDATE bookings SET status='Cancelled', payment_status=? WHERE id=?", (new_payment, booking["id"]))
    execute("UPDATE treks SET available_slots = available_slots + ? WHERE id=? AND status != 'Completed'",
            (booking["people"], booking["trek_id"]))
    if refund:
        notify(booking["user_id"], "Refund processed: Rs. " + str(int(refund)) + " for booking #" + str(booking["id"]))
    cache_clear()
    return refund


# ---------------- celery jobs ----------------
def run_job(name, *args):
    """Send the job to celery. If celery/redis is not running, run it in a thread instead."""
    try:
        from celery_app import celery
        celery.send_task("trekison." + name, args=args, retry=False)
    except Exception:
        import jobs
        print("Celery not available, running", name, "directly")
        threading.Thread(target=getattr(jobs, name), args=args, daemon=True).start()
