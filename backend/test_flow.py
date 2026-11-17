"""Run:  python test_flow.py     (needs only Flask; fakes Redis/Celery)"""
import os, sys, tempfile, types, time

tmp = tempfile.mkdtemp()
os.environ["TREKISON_DB"] = os.path.join(tmp, "t.sqlite3")
os.environ["TREKISON_INSTANCE_DIR"] = tmp
try:
    import redis  # noqa
except ImportError:
    fake = types.ModuleType("redis")
    class _R:
        @classmethod
        def from_url(cls, *a, **k): return cls()
        def get(self, k): raise ConnectionError
        def setex(self, *a): raise ConnectionError
        def delete(self, *a): raise ConnectionError
    fake.Redis = _R
    sys.modules["redis"] = fake

from app import app
from datetime import date, timedelta
c = app.test_client()
ok = lambda r, code=200: (r.status_code == code) or sys.exit(f"FAIL {r.status_code} {r.get_json()}")
def hdr(t): return {"Authorization": f"Bearer {t}"}
def login(e, p):
    r = c.post("/api/auth/login", json={"email": e, "password": p}); ok(r); return r.get_json()["token"]

admin = login("admin@trekison.com", "Admin@123")
# admin adds staff
ok(c.post("/api/admin/staff", headers=hdr(admin), json={"name": "Sam Guide", "email": "sam@x.com", "password": "secret1", "phone": "9999999999", "experience_years": 4}), 201)
staff_id = c.get("/api/admin/staff", headers=hdr(admin)).get_json()["staff"][0]["id"]
start = (date.today() + timedelta(days=5)).isoformat(); end = (date.today() + timedelta(days=7)).isoformat()
r = c.post("/api/admin/treks", headers=hdr(admin), json={"name": "Test Peak", "location": "Hills", "difficulty": "Easy",
        "start_date": start, "end_date": end, "total_slots": 12, "price": 1000, "staff_id": staff_id}); ok(r, 201)
trek = c.get("/api/admin/treks", headers=hdr(admin)).get_json()["treks"][0]
tid = trek["id"]
assert trek["duration_days"] == 3
# date clash rules for staff: same days, and the 2 day gap
def new_trek(name, s, e):
    return c.post("/api/admin/treks", headers=hdr(admin), json={"name": name, "location": "X", "difficulty": "Easy",
        "start_date": (date.today() + timedelta(days=s)).isoformat(), "end_date": (date.today() + timedelta(days=e)).isoformat(),
        "total_slots": 5, "price": 0, "staff_id": staff_id})
ok(new_trek("Overlap", 6, 12), 400)       # clashes with days 5..7
ok(new_trek("Too close", 9, 12), 400)     # only 1 free day after the first trek
ok(new_trek("Ok after gap", 10, 12), 201) # days 8 and 9 are free -> allowed
ok(new_trek("Too close before", 1, 3), 400)  # only 1 free day before the first trek
ok(new_trek("Ok before gap", 1, 2), 201)     # days 3 and 4 are free -> allowed
ok(c.post(f"/api/admin/treks/{tid}/approve", headers=hdr(admin)))

staff = login("sam@x.com", "secret1")
ok(c.put(f"/api/staff/treks/{tid}", headers=hdr(staff), json={"status": "Open"}))

ok(c.post("/api/auth/register", json={"name": "Tia", "email": "tia@x.com", "password": "secret1"}), 201)
ok(c.post("/api/auth/register", json={"name": "Tia", "email": "tia@x.com", "password": "secret1"}), 409)
u1 = login("tia@x.com", "secret1")
ok(c.post("/api/auth/register", json={"name": "Raj", "email": "raj@x.com", "password": "secret1"}), 201)
u2 = login("raj@x.com", "secret1")

people = lambda n: [{"name": f"P{i}", "age": 25} for i in range(n)]
assert len(c.get("/api/treks", headers=hdr(u1)).get_json()["treks"]) == 1
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(u1), json={"participants": people(11)}), 400)      # >10 refused
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(u1), json={"participants": people(10)}), 201)      # 10 ok
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(u1), json={"participants": people(1)}), 409)       # duplicate
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(u2), json={"participants": people(3)}), 409)       # only 2 left
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(u2), json={"participants": people(2)}), 201)       # fills it
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(u2), json={"participants": people(1)}), 409)
assert [t for t in c.get("/api/admin/treks", headers=hdr(admin)).get_json()["treks"] if t["id"] == tid][0]["available_slots"] == 0

# staff sees registered users; other roles are blocked
p = c.get(f"/api/staff/treks/{tid}/participants", headers=hdr(staff)).get_json()
assert sum(b["people"] for b in p["bookings"]) == 12
ok(c.get("/api/admin/stats", headers=hdr(staff)), 403)
ok(c.get(f"/api/staff/treks/{tid}/participants", headers=hdr(u1)), 403)

# cancel frees seats
bid = c.get("/api/bookings", headers=hdr(u2)).get_json()["bookings"][0]["id"]
ok(c.post(f"/api/bookings/{bid}/pay", headers=hdr(u2)))
r = c.post(f"/api/bookings/{bid}/cancel", headers=hdr(u2)); ok(r)
assert "Refund" in r.get_json()["message"], r.get_json()
assert c.get("/api/bookings", headers=hdr(u2)).get_json()["bookings"][0]["payment_status"] == "Refunded"
assert [t for t in c.get("/api/admin/treks", headers=hdr(admin)).get_json()["treks"] if t["id"] == tid][0]["available_slots"] == 2
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(u2), json={"participants": people(1)}), 201)       # re-book after cancel

# closing blocks booking
ok(c.put(f"/api/staff/treks/{tid}", headers=hdr(staff), json={"status": "Closed"}))
ok(c.post("/api/auth/register", json={"name": "Z", "email": "z@x.com", "password": "secret1"}), 201)
ok(c.post(f"/api/treks/{tid}/book", headers=hdr(login("z@x.com", "secret1")), json={"participants": people(1)}), 400)

# blacklist blocks login
uid = [u for u in c.get("/api/admin/users?q=raj", headers=hdr(admin)).get_json()["users"]][0]["id"]
ok(c.post(f"/api/admin/users/{uid}/status", headers=hdr(admin), json={"status": "blacklisted"}))
ok(c.post("/api/auth/login", json={"email": "raj@x.com", "password": "secret1"}), 403)
ok(c.get("/api/bookings", headers=hdr(u2)), 403)

# staff start / complete
ok(c.post(f"/api/staff/treks/{tid}/complete", headers=hdr(staff)), 400)
ok(c.post(f"/api/staff/treks/{tid}/start", headers=hdr(staff)))
ok(c.post(f"/api/staff/treks/{tid}/complete", headers=hdr(staff)))
assert c.get("/api/bookings", headers=hdr(u1)).get_json()["bookings"][0]["status"] == "Completed"

# CSV export job (runs in thread fallback)
r = c.post("/api/exports", headers=hdr(u1)); ok(r, 202)
for _ in range(30):
    ex = c.get("/api/exports", headers=hdr(u1)).get_json()["exports"][0]
    if ex["status"] == "Done": break
    time.sleep(0.2)
assert ex["status"] == "Done", ex
csv_text = c.get(f"/api/exports/{ex['id']}/download", headers=hdr(u1)).data.decode()
assert "Test Peak" in csv_text, csv_text
print(csv_text)

# jobs: reminders + monthly report
import jobs
n = jobs.send_daily_reminders(today=date.today() + timedelta(days=4))
print("reminders sent:", n)
print("report:", jobs.send_monthly_report(today=date.today() + timedelta(days=40)))
stats = c.get("/api/admin/stats", headers=hdr(admin)).get_json()
print(stats["totals"])
print("ALL TESTS PASSED")
