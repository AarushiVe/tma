import os
from datetime import date
from flask import Blueprint, request, jsonify, g, send_file
import config
from db import get_db, query, query_one, execute
from helpers import (error, login_required, notify, get_open_treks, get_trek, cache_clear,
                     update_finished_treks, BOOKING_QUERY, add_participants, cancel_booking, run_job)

trekker_bp = Blueprint("trekker", __name__, url_prefix="/api")


@trekker_bp.route("/treks")
@login_required("trekker")
def browse_treks():
    treks = get_open_treks()

    # search and filters
    q = request.args.get("q", "").strip().lower()
    difficulty = request.args.get("difficulty", "")
    location = request.args.get("location", "")
    min_days = request.args.get("min_days", type=int)
    max_days = request.args.get("max_days", type=int)

    result = []
    for t in treks:
        if q and q not in t["name"].lower() and q not in t["location"].lower():
            continue
        if difficulty and t["difficulty"] != difficulty:
            continue
        if location and t["location"] != location:
            continue
        if min_days and t["duration_days"] < min_days:
            continue
        if max_days and t["duration_days"] > max_days:
            continue
        result.append(t)

    locations = sorted(set(t["location"] for t in treks))
    return jsonify(treks=result, locations=locations, max_people=config.MAX_PEOPLE)


@trekker_bp.route("/treks/<int:trek_id>/book", methods=["POST"])
@login_required("trekker")
def book_trek(trek_id):
    data = request.get_json() or {}
    people = data.get("participants")

    if not isinstance(people, list) or len(people) == 0:
        return error("Add at least one person")
    if len(people) > config.MAX_PEOPLE:
        return error("You can book for maximum " + str(config.MAX_PEOPLE) + " people")

    # check every person's details
    for i, p in enumerate(people, start=1):
        if not str(p.get("name", "")).strip():
            return error("Enter the name of person " + str(i))
        try:
            age = int(p.get("age"))
        except (TypeError, ValueError):
            return error("Enter a valid age for person " + str(i))
        if age < 5 or age > 90:
            return error("Age of person " + str(i) + " must be between 5 and 90")

    update_finished_treks()
    trek = get_trek(trek_id)
    if trek is None:
        return error("Trek not found", 404)
    if trek["status"] != "Open":
        return error("This trek is not open for booking")
    if trek["is_started"] or trek["start_date"] <= date.today().isoformat():
        return error("Booking is closed for this trek")

    old = query_one("SELECT id FROM bookings WHERE user_id=? AND trek_id=? AND status != 'Cancelled'",
                    (g.user["id"], trek_id))
    if old:
        return error("You have already booked this trek", 409)

    n = len(people)
    db = get_db()
    # this update only works if enough slots are left, so it can never overbook
    cur = db.execute("UPDATE treks SET available_slots = available_slots - ? "
                     "WHERE id=? AND available_slots >= ?", (n, trek_id, n))
    if cur.rowcount == 0:
        db.rollback()
        return error("Not enough slots left. Only " + str(trek["available_slots"]) + " available", 409)

    cur = db.execute("INSERT INTO bookings (user_id, trek_id, people) VALUES (?, ?, ?)", (g.user["id"], trek_id, n))
    booking_id = cur.lastrowid
    for p in people:
        db.execute("INSERT INTO participants (booking_id, name, age, phone) VALUES (?, ?, ?, ?)",
                   (booking_id, p["name"].strip(), int(p["age"]), p.get("phone", "")))
    db.commit()

    cache_clear()
    notify(g.user["id"], "Booking confirmed for " + trek["name"] + " (" + str(n) + " people)")
    if trek["staff_id"]:
        notify(trek["staff_id"], g.user["name"] + " booked " + str(n) + " slots in " + trek["name"])
    return jsonify(message="Booking confirmed!"), 201


@trekker_bp.route("/bookings")
@login_required("trekker")
def my_bookings():
    update_finished_treks()
    bookings = query(BOOKING_QUERY + " WHERE b.user_id=? ORDER BY b.id DESC", (g.user["id"],))
    return jsonify(bookings=add_participants(bookings))


def find_my_booking(booking_id):
    return query_one("SELECT * FROM bookings WHERE id=? AND user_id=?", (booking_id, g.user["id"]))


@trekker_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required("trekker")
def cancel(booking_id):
    booking = find_my_booking(booking_id)
    if booking is None:
        return error("Booking not found", 404)
    if booking["status"] != "Booked":
        return error("Only active bookings can be cancelled")
    trek = get_trek(booking["trek_id"])
    if trek["is_started"] or trek["start_date"] <= date.today().isoformat():
        return error("Trek already started, cannot cancel")

    refund = cancel_booking(booking)
    notify(g.user["id"], "Booking cancelled for " + trek["name"])
    if trek["staff_id"]:
        notify(trek["staff_id"], g.user["name"] + " cancelled booking for " + trek["name"])
    if refund:
        return jsonify(message="Booking cancelled. Refund of Rs. " + str(int(refund)) + " processed.")
    return jsonify(message="Booking cancelled")


@trekker_bp.route("/bookings/<int:booking_id>/pay", methods=["POST"])
@login_required("trekker")
def pay(booking_id):
    # fake payment, just marks the booking as paid
    booking = find_my_booking(booking_id)
    if booking is None:
        return error("Booking not found", 404)
    if booking["status"] != "Booked" or booking["payment_status"] == "Paid":
        return error("Cannot pay for this booking")
    execute("UPDATE bookings SET payment_status='Paid' WHERE id=?", (booking_id,))
    notify(g.user["id"], "Payment done for booking #" + str(booking_id))
    return jsonify(message="Payment successful (demo)")


# ---------------- notifications ----------------
@trekker_bp.route("/notifications")
@login_required()
def get_notifications():
    rows = query("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 50", (g.user["id"],))
    unread = query_one("SELECT COUNT(*) AS c FROM notifications WHERE user_id=? AND is_read=0", (g.user["id"],))
    return jsonify(notifications=rows, unread=unread["c"])


@trekker_bp.route("/notifications/read", methods=["POST"])
@login_required()
def mark_read():
    execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (g.user["id"],))
    return jsonify(message="ok")


# ---------------- export booking history as csv (celery job) ----------------
@trekker_bp.route("/exports", methods=["POST"])
@login_required("trekker")
def start_export():
    export_id = execute("INSERT INTO exports (user_id) VALUES (?)", (g.user["id"],))
    run_job("export_booking_history", export_id)
    return jsonify(message="Export started, you will get a notification when it is ready", export_id=export_id), 202


@trekker_bp.route("/exports")
@login_required("trekker")
def list_exports():
    rows = query("SELECT id, status, created_at FROM exports WHERE user_id=? ORDER BY id DESC LIMIT 5", (g.user["id"],))
    return jsonify(exports=rows)


@trekker_bp.route("/exports/<int:export_id>/download")
@login_required("trekker")
def download_export(export_id):
    ex = query_one("SELECT * FROM exports WHERE id=? AND user_id=?", (export_id, g.user["id"]))
    if ex is None or ex["status"] != "Done":
        return error("File is not ready", 404)
    return send_file(os.path.join(config.EXPORT_DIR, ex["filename"]), as_attachment=True,
                     download_name="my_trekking_history.csv")
