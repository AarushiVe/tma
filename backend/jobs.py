"""The code of the 3 background jobs. celery_app.py just calls these functions."""
import csv
import os
from datetime import date, timedelta
import config
import mail
from db import connect


def add_notification(conn, user_id, message):
    conn.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, message))
    conn.commit()


# ---------- 1. daily reminder ----------
def send_daily_reminders(today=None):
    if today is None:
        today = date.today()
    last_day = today + timedelta(days=config.REMINDER_DAYS)
    conn = connect()

    rows = conn.execute("""
        SELECT b.people, u.id AS user_id, u.name AS user_name, u.email,
               t.name AS trek_name, t.location, t.start_date, t.instructions
        FROM bookings b JOIN users u ON u.id = b.user_id JOIN treks t ON t.id = b.trek_id
        WHERE b.status = 'Booked' AND t.status != 'Completed' AND u.status = 'active'
        AND t.start_date BETWEEN ? AND ?""", (today.isoformat(), last_day.isoformat())).fetchall()

    for r in rows:
        add_notification(conn, r["user_id"], "Reminder: " + r["trek_name"] + " starts on " + r["start_date"])
        html = ("<h3>Trek reminder</h3>"
                "<p>Hi " + r["user_name"] + ",</p>"
                "<p>Your trek <b>" + r["trek_name"] + "</b> (" + r["location"] + ") starts on <b>"
                + r["start_date"] + "</b> for " + str(r["people"]) + " people.</p>"
                "<p>Instructions: " + (r["instructions"] or "Carry water and wear trekking shoes.") + "</p>"
                "<p>Team Trekison</p>")
        try:
            mail.send_email(r["email"], "Reminder: " + r["trek_name"], html)
            mail.send_gchat("Reminder: " + r["user_name"] + " has " + r["trek_name"] + " on " + r["start_date"])
        except Exception as e:
            print("Reminder failed:", e)

    conn.close()
    return len(rows)


# ---------- 2. monthly report ----------
def send_monthly_report(today=None):
    """Runs on the 1st of every month and reports about the last month."""
    if today is None:
        today = date.today()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    start = last_month_end.replace(day=1).isoformat()
    end = first_of_this_month.isoformat()
    conn = connect()

    def one(sql, args):
        return conn.execute(sql, args).fetchone()[0]

    treks_done = one("SELECT COUNT(*) FROM treks WHERE status='Completed' AND end_date >= ? AND end_date < ?", (start, end))
    people = one("""SELECT COALESCE(SUM(b.people), 0) FROM bookings b JOIN treks t ON t.id = b.trek_id
                    WHERE b.status='Completed' AND t.end_date >= ? AND t.end_date < ?""", (start, end))
    bookings = one("SELECT COUNT(*) FROM bookings WHERE booking_date >= ? AND booking_date < ?", (start, end))
    popular = conn.execute("""SELECT t.name, SUM(b.people) AS people FROM bookings b JOIN treks t ON t.id = b.trek_id
                              WHERE b.status != 'Cancelled' AND b.booking_date >= ? AND b.booking_date < ?
                              GROUP BY t.id ORDER BY people DESC LIMIT 5""", (start, end)).fetchall()

    rows = ""
    for p in popular:
        rows += "<tr><td>" + p["name"] + "</td><td>" + str(p["people"]) + "</td></tr>"
    if rows == "":
        rows = "<tr><td colspan='2'>No bookings this month</td></tr>"

    month_name = last_month_end.strftime("%B %Y")
    html = ("<h2>Trekison Monthly Report - " + month_name + "</h2>"
            "<ul><li>Treks conducted: " + str(treks_done) + "</li>"
            "<li>Users participated: " + str(people) + "</li>"
            "<li>New bookings: " + str(bookings) + "</li></ul>"
            "<h3>Popular treks</h3>"
            "<table border='1' cellpadding='6' style='border-collapse:collapse'>"
            "<tr style='background:#0d6efd;color:white'><th>Trek</th><th>People</th></tr>" + rows + "</table>")

    path = os.path.join(config.REPORT_DIR, "report_" + last_month_end.strftime("%Y_%m") + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    admin = conn.execute("SELECT id, email FROM users WHERE role='admin'").fetchone()
    mail.send_email(admin["email"], "Trekison monthly report - " + month_name, html)
    add_notification(conn, admin["id"], "Monthly report for " + month_name + " was emailed")
    conn.close()
    return path


# ---------- 3. csv export (started by the user) ----------
def export_booking_history(export_id):
    conn = connect()
    export = conn.execute("SELECT * FROM exports WHERE id=?", (export_id,)).fetchone()
    if export is None:
        return
    try:
        rows = conn.execute("""SELECT b.user_id, t.name, t.location, b.people, b.status, b.payment_status, t.start_date, t.end_date
                               FROM bookings b JOIN treks t ON t.id = b.trek_id
                               WHERE b.user_id = ? ORDER BY b.id DESC""", (export["user_id"],)).fetchall()
        filename = "export_" + str(export_id) + ".csv"
        with open(os.path.join(config.EXPORT_DIR, filename), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["User ID", "Trek Name", "Location", "People", "Booking Status", "Payment Status", "Start Date", "End Date"])
            for r in rows:
                writer.writerow(list(r))
        conn.execute("UPDATE exports SET status='Done', filename=? WHERE id=?", (filename, export_id))
        conn.commit()
        add_notification(conn, export["user_id"], "Your booking history CSV is ready. Download it from My Bookings.")
    except Exception as e:
        print("Export failed:", e)
        conn.execute("UPDATE exports SET status='Failed' WHERE id=?", (export_id,))
        conn.commit()
        add_notification(conn, export["user_id"], "Sorry, your export failed. Please try again.")
    conn.close()
