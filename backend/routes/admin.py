import re
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from db import query, query_one, execute
import config
from helpers import (error, login_required, notify, get_trek, cache_clear, update_finished_treks,
                     TREK_QUERY, BOOKING_QUERY, add_participants, run_job)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ---------------- dashboard ----------------
@admin_bp.route("/stats")
@login_required("admin")
def stats():
    update_finished_treks()

    def count(sql):
        return query_one(sql)["c"]

    totals = {
        "treks": count("SELECT COUNT(*) AS c FROM treks"),
        "open_treks": count("SELECT COUNT(*) AS c FROM treks WHERE status='Open'"),
        "users": count("SELECT COUNT(*) AS c FROM users WHERE role='trekker'"),
        "staff": count("SELECT COUNT(*) AS c FROM users WHERE role='staff'"),
        "bookings": count("SELECT COUNT(*) AS c FROM bookings"),
        "people": count("SELECT COALESCE(SUM(people),0) AS c FROM bookings WHERE status != 'Cancelled'"),
    }
    popular = query("""SELECT t.name, COALESCE(SUM(b.people), 0) AS people
                       FROM treks t LEFT JOIN bookings b ON b.trek_id = t.id AND b.status != 'Cancelled'
                       GROUP BY t.id ORDER BY people DESC LIMIT 5""")
    by_status = query("SELECT status, COUNT(*) AS count FROM treks GROUP BY status")
    return jsonify(totals=totals, popular=popular, by_status=by_status)


@admin_bp.route("/reports/monthly", methods=["POST"])
@login_required("admin")
def monthly_report():
    run_job("send_monthly_report")
    return jsonify(message="Report is being generated and will be emailed"), 202


# ---------------- treks ----------------
def read_trek_form(data, is_new):
    """checks the trek form. returns (values, error_message)"""
    name = (data.get("name") or "").strip()
    location = (data.get("location") or "").strip()
    if name == "" or location == "":
        return None, "Name and location are required"
    if data.get("difficulty") not in ("Easy", "Moderate", "Hard"):
        return None, "Choose a difficulty"
    try:
        start = datetime.strptime(data.get("start_date") or "", "%Y-%m-%d").date()
        end = datetime.strptime(data.get("end_date") or "", "%Y-%m-%d").date()
    except ValueError:
        return None, "Enter valid start and end dates"
    if end < start:
        return None, "End date cannot be before start date"
    if is_new and start < date.today():
        return None, "Start date cannot be in the past"
    try:
        slots = int(data.get("total_slots"))
        price = float(data.get("price") or 0)
    except (TypeError, ValueError):
        return None, "Slots and price must be numbers"
    if slots < 1 or slots > 500:
        return None, "Slots must be between 1 and 500"
    if price < 0:
        return None, "Price cannot be negative"

    values = {
        "name": name, "location": location, "difficulty": data["difficulty"],
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "duration_days": (end - start).days + 1, "total_slots": slots, "price": price,
        "description": (data.get("description") or "").strip(),
        "instructions": (data.get("instructions") or "").strip(),
    }
    return values, None


def check_staff(staff_id, start_date=None, end_date=None, ignore_trek_id=None, check_active=True):
    """returns an error message if this staff member cannot be given the trek, else None"""
    if not staff_id:
        return None
    staff = query_one("SELECT * FROM users WHERE id=? AND role='staff'", (staff_id,))
    if staff is None:
        return "Staff member not found"
    if check_active and staff["status"] != "active":
        return "This staff member is not active"
    if start_date is None:
        return None

    # a staff member cannot have two treks on the same days, and needs a gap between treks
    gap = config.STAFF_GAP_DAYS
    new_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    new_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    others = query("SELECT * FROM treks WHERE staff_id=? AND status != 'Completed' AND id != ?",
                   (staff_id, ignore_trek_id or 0))
    for t in others:
        old_start = datetime.strptime(t["start_date"], "%Y-%m-%d").date()
        old_end = datetime.strptime(t["end_date"], "%Y-%m-%d").date()
        if new_start <= old_end + timedelta(days=gap) and old_start <= new_end + timedelta(days=gap):
            free_from = old_end + timedelta(days=gap + 1)
            return (staff["name"] + " is already assigned to " + t["name"] + " (" + t["start_date"] + " to "
                    + t["end_date"] + "). Staff need " + str(gap) + " free days between treks, so the earliest "
                    "new trek can start on " + free_from.isoformat() + " or the new trek must end before "
                    + (old_start - timedelta(days=gap + 1)).isoformat() + ".")
    return None


@admin_bp.route("/treks")
@login_required("admin")
def list_treks():
    update_finished_treks()
    sql = TREK_QUERY + " WHERE 1=1"
    args = []
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    if q:
        sql += " AND (t.name LIKE ? OR t.location LIKE ? OR u.name LIKE ?)"
        args += ["%" + q + "%"] * 3
    if status:
        sql += " AND t.status = ?"
        args.append(status)
    return jsonify(treks=query(sql + " ORDER BY t.start_date DESC", args))


@admin_bp.route("/treks", methods=["POST"])
@login_required("admin")
def create_trek():
    data = request.get_json() or {}
    v, msg = read_trek_form(data, True)
    if msg:
        return error(msg)
    staff_id = data.get("staff_id") or None
    msg = check_staff(staff_id, v["start_date"], v["end_date"])
    if msg:
        return error(msg)

    execute("""INSERT INTO treks (name, location, difficulty, duration_days, total_slots, available_slots,
               price, description, instructions, staff_id, start_date, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (v["name"], v["location"], v["difficulty"], v["duration_days"], v["total_slots"], v["total_slots"],
             v["price"], v["description"], v["instructions"], staff_id, v["start_date"], v["end_date"]))
    cache_clear()
    if staff_id:
        notify(staff_id, "You were assigned to the trek " + v["name"])
    return jsonify(message="Trek created with status Pending"), 201


@admin_bp.route("/treks/<int:trek_id>", methods=["PUT"])
@login_required("admin")
def update_trek(trek_id):
    trek = get_trek(trek_id)
    if trek is None:
        return error("Trek not found", 404)
    data = request.get_json() or {}
    v, msg = read_trek_form(data, False)
    if msg:
        return error(msg)

    if v["total_slots"] < trek["registered"]:
        return error(str(trek["registered"]) + " people already booked, slots cannot be less than that")
    staff_id = data.get("staff_id") or None
    # only check "active" when the staff member is changed, but always check the dates
    msg = check_staff(staff_id, v["start_date"], v["end_date"], trek_id, check_active=(staff_id != trek["staff_id"]))
    if msg:
        return error(msg)
    status = data.get("status") or trek["status"]
    if status not in ("Pending", "Approved", "Open", "Closed", "Completed"):
        return error("Invalid status")
    if status in ("Approved", "Open") and not staff_id:
        return error("Assign a staff member first")

    available = v["total_slots"] - trek["registered"]
    execute("""UPDATE treks SET name=?, location=?, difficulty=?, duration_days=?, total_slots=?,
               available_slots=?, price=?, description=?, instructions=?, staff_id=?,
               start_date=?, end_date=?, status=? WHERE id=?""",
            (v["name"], v["location"], v["difficulty"], v["duration_days"], v["total_slots"], available,
             v["price"], v["description"], v["instructions"], staff_id, v["start_date"], v["end_date"],
             status, trek_id))
    if status == "Completed":
        execute("UPDATE bookings SET status='Completed' WHERE trek_id=? AND status='Booked'", (trek_id,))
    cache_clear()
    return jsonify(message="Trek updated")


@admin_bp.route("/treks/<int:trek_id>/assign", methods=["POST"])
@login_required("admin")
def assign_staff(trek_id):
    trek = get_trek(trek_id)
    if trek is None:
        return error("Trek not found", 404)
    if trek["status"] == "Completed":
        return error("Completed trek cannot be changed")
    staff_id = (request.get_json() or {}).get("staff_id") or None
    msg = check_staff(staff_id, trek["start_date"], trek["end_date"], trek_id)
    if msg:
        return error(msg)
    execute("UPDATE treks SET staff_id=? WHERE id=?", (staff_id, trek_id))
    cache_clear()
    if staff_id:
        notify(staff_id, "You were assigned to the trek " + trek["name"])
    return jsonify(message="Staff assigned")


@admin_bp.route("/treks/<int:trek_id>/approve", methods=["POST"])
@login_required("admin")
def approve_trek(trek_id):
    trek = get_trek(trek_id)
    if trek is None:
        return error("Trek not found", 404)
    if trek["status"] != "Pending":
        return error("Only pending treks can be approved")
    if not trek["staff_id"]:
        return error("Assign a staff member before approving")
    execute("UPDATE treks SET status='Approved' WHERE id=?", (trek_id,))
    cache_clear()
    notify(trek["staff_id"], trek["name"] + " is approved. You can open it for booking now.")
    return jsonify(message="Trek approved")


@admin_bp.route("/treks/<int:trek_id>", methods=["DELETE"])
@login_required("admin")
def delete_trek(trek_id):
    trek = get_trek(trek_id)
    if trek is None:
        return error("Trek not found", 404)
    if trek["booking_count"] > 0:
        return error("This trek has bookings, so it cannot be deleted")
    execute("DELETE FROM treks WHERE id=?", (trek_id,))
    cache_clear()
    return jsonify(message="Trek deleted")


# ---------------- staff ----------------
STAFF_QUERY = """
SELECT u.id, u.name, u.email, u.phone, u.status, p.experience_years, p.specialization,
       (SELECT COUNT(*) FROM treks t WHERE t.staff_id = u.id) AS trek_count
FROM users u LEFT JOIN staff_profiles p ON p.user_id = u.id
WHERE u.role = 'staff'
"""


def read_staff_form(data):
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if name == "":
        return None, "Name is required"
    if not re.fullmatch(r"\+?[0-9 \-]{7,15}", phone):
        return None, "Enter a valid phone number"
    try:
        years = int(data.get("experience_years") or 0)
    except ValueError:
        return None, "Experience must be a number"
    if years < 0 or years > 60:
        return None, "Experience must be between 0 and 60"
    return (name, phone, years, (data.get("specialization") or "").strip()), None


@admin_bp.route("/staff")
@login_required("admin")
def list_staff():
    sql = STAFF_QUERY
    args = []
    q = request.args.get("q", "").strip()
    if q:
        sql += " AND (u.name LIKE ? OR u.email LIKE ? OR u.phone LIKE ?)"
        args = ["%" + q + "%"] * 3
    return jsonify(staff=query(sql + " ORDER BY u.name", args))


@admin_bp.route("/staff", methods=["POST"])
@login_required("admin")
def add_staff():
    data = request.get_json() or {}
    values, msg = read_staff_form(data)
    if msg:
        return error(msg)
    name, phone, years, spec = values
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if "@" not in email:
        return error("Enter a valid email")
    if len(password) < 6:
        return error("Password must be at least 6 characters")
    if query_one("SELECT id FROM users WHERE email=?", (email,)):
        return error("This email is already used", 409)

    user_id = execute("INSERT INTO users (name, email, password, phone, role) VALUES (?, ?, ?, ?, 'staff')",
                      (name, email, generate_password_hash(password), phone))
    execute("INSERT INTO staff_profiles (user_id, experience_years, specialization) VALUES (?, ?, ?)",
            (user_id, years, spec))
    return jsonify(message="Staff added"), 201


@admin_bp.route("/staff/<int:user_id>", methods=["PUT"])
@login_required("admin")
def edit_staff(user_id):
    if query_one("SELECT id FROM users WHERE id=? AND role='staff'", (user_id,)) is None:
        return error("Staff not found", 404)
    values, msg = read_staff_form(request.get_json() or {})
    if msg:
        return error(msg)
    name, phone, years, spec = values
    execute("UPDATE users SET name=?, phone=? WHERE id=?", (name, phone, user_id))
    execute("DELETE FROM staff_profiles WHERE user_id=?", (user_id,))
    execute("INSERT INTO staff_profiles (user_id, experience_years, specialization) VALUES (?, ?, ?)",
            (user_id, years, spec))
    return jsonify(message="Staff updated")


# ---------------- users ----------------
@admin_bp.route("/users")
@login_required("admin")
def list_users():
    sql = """SELECT u.id, u.name, u.email, u.phone, u.status, u.created_at,
             (SELECT COUNT(*) FROM bookings b WHERE b.user_id = u.id) AS booking_count
             FROM users u WHERE u.role = 'trekker'"""
    args = []
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    if q:
        sql += " AND (u.name LIKE ? OR u.email LIKE ? OR u.phone LIKE ?)"
        args += ["%" + q + "%"] * 3
    if status:
        sql += " AND u.status = ?"
        args.append(status)
    return jsonify(users=query(sql + " ORDER BY u.id DESC", args))


@admin_bp.route("/users/<int:user_id>/status", methods=["POST"])
@login_required("admin")
def set_status(user_id):
    """activate / deactivate / blacklist a trekker or a staff member"""
    status = (request.get_json() or {}).get("status")
    if status not in ("active", "deactivated", "blacklisted"):
        return error("Invalid status")
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user is None or user["role"] == "admin":
        return error("User not found", 404)

    execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
    if user["role"] == "staff" and status != "active":
        # the admin has to assign their treks to someone else
        execute("UPDATE treks SET staff_id=NULL WHERE staff_id=? AND status != 'Completed'", (user_id,))
        cache_clear()
    return jsonify(message=user["name"] + " is now " + status)


# ---------------- bookings ----------------
@admin_bp.route("/bookings")
@login_required("admin")
def all_bookings():
    update_finished_treks()
    sql = BOOKING_QUERY + " WHERE 1=1"
    args = []
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    if q:
        sql += " AND (u.name LIKE ? OR u.email LIKE ? OR t.name LIKE ?)"
        args += ["%" + q + "%"] * 3
    if status:
        sql += " AND b.status = ?"
        args.append(status)
    bookings = query(sql + " ORDER BY b.id DESC", args)
    return jsonify(bookings=add_participants(bookings))
