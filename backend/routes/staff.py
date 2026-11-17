from flask import Blueprint, request, jsonify, g
from db import query, execute
from helpers import (error, login_required, notify, get_trek, cache_clear, update_finished_treks,
                     TREK_QUERY, BOOKING_QUERY, add_participants, cancel_booking)

staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")


def my_trek(trek_id):
    """returns (trek, error). Only the assigned staff can manage a trek"""
    trek = get_trek(trek_id)
    if trek is None:
        return None, error("Trek not found", 404)
    if trek["staff_id"] != g.user["id"]:
        return None, error("This trek is not assigned to you", 403)
    return trek, None


def notify_trekkers(trek_id, message):
    rows = query("SELECT DISTINCT user_id FROM bookings WHERE trek_id=? AND status='Booked'", (trek_id,))
    for r in rows:
        notify(r["user_id"], message)


@staff_bp.route("/treks")
@login_required("staff")
def assigned_treks():
    update_finished_treks()
    treks = query(TREK_QUERY + " WHERE t.staff_id=? ORDER BY t.start_date DESC", (g.user["id"],))
    return jsonify(treks=treks)


@staff_bp.route("/treks/<int:trek_id>/participants")
@login_required("staff")
def participants(trek_id):
    trek, err = my_trek(trek_id)
    if err:
        return err
    bookings = query(BOOKING_QUERY + " WHERE b.trek_id=? AND b.status != 'Cancelled' ORDER BY b.id", (trek_id,))
    return jsonify(trek=trek, bookings=add_participants(bookings))


@staff_bp.route("/treks/<int:trek_id>", methods=["PUT"])
@login_required("staff")
def update_trek(trek_id):
    trek, err = my_trek(trek_id)
    if err:
        return err
    data = request.get_json() or {}
    if trek["status"] == "Completed":
        return error("Completed trek cannot be changed")

    slots = trek["available_slots"]
    total = trek["total_slots"]
    status = trek["status"]

    if data.get("available_slots") not in (None, ""):
        try:
            slots = int(data["available_slots"])
        except ValueError:
            return error("Slots must be a number")
        if slots < 0 or slots > 500:
            return error("Slots must be between 0 and 500")
        if slots > total:
            total = slots

    if data.get("status"):
        if data["status"] not in ("Open", "Closed"):
            return error("Staff can only set Open or Closed")
        if trek["status"] == "Pending":
            return error("Wait for admin to approve this trek")
        if trek["is_started"]:
            return error("Trek already started")
        status = data["status"]

    execute("UPDATE treks SET available_slots=?, total_slots=?, status=? WHERE id=?", (slots, total, status, trek_id))
    cache_clear()
    return jsonify(message="Trek updated")


@staff_bp.route("/treks/<int:trek_id>/start", methods=["POST"])
@login_required("staff")
def start_trek(trek_id):
    trek, err = my_trek(trek_id)
    if err:
        return err
    if trek["status"] not in ("Approved", "Open", "Closed") or trek["is_started"]:
        return error("This trek cannot be started")
    # once started, no more bookings
    execute("UPDATE treks SET is_started=1, status='Closed' WHERE id=?", (trek_id,))
    cache_clear()
    notify_trekkers(trek_id, "Your trek " + trek["name"] + " has started!")
    return jsonify(message="Trek marked as started")


@staff_bp.route("/treks/<int:trek_id>/complete", methods=["POST"])
@login_required("staff")
def complete_trek(trek_id):
    trek, err = my_trek(trek_id)
    if err:
        return err
    if not trek["is_started"]:
        return error("Start the trek first")
    if trek["status"] == "Completed":
        return error("Already completed")
    execute("UPDATE treks SET status='Completed' WHERE id=?", (trek_id,))
    execute("UPDATE bookings SET status='Completed' WHERE trek_id=? AND status='Booked'", (trek_id,))
    cache_clear()
    notify_trekkers(trek_id, "Your trek " + trek["name"] + " is completed. Hope you enjoyed it!")
    return jsonify(message="Trek marked as completed")


@staff_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required("staff")
def remove_booking(booking_id):
    rows = query("SELECT * FROM bookings WHERE id=?", (booking_id,))
    if not rows:
        return error("Booking not found", 404)
    booking = rows[0]
    trek, err = my_trek(booking["trek_id"])
    if err:
        return err
    if booking["status"] != "Booked" or trek["is_started"]:
        return error("This booking cannot be removed")
    refund = cancel_booking(booking)
    notify(booking["user_id"], "Your booking for " + trek["name"] + " was cancelled by the staff")
    if refund:
        return jsonify(message="Booking removed. Refund of Rs. " + str(int(refund)) + " processed.")
    return jsonify(message="Booking removed")
