import re
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from db import query_one, execute
from helpers import error, make_token, login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def user_info(u):
    return {"id": u["id"], "name": u["name"], "email": u["email"], "phone": u["phone"],
            "role": u["role"], "status": u["status"]}


def valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone = (data.get("phone") or "").strip()

    if name == "":
        return error("Name is required")
    if not valid_email(email):
        return error("Enter a valid email")
    if len(password) < 6:
        return error("Password must be at least 6 characters")
    if query_one("SELECT id FROM users WHERE email=?", (email,)):
        return error("This email is already registered", 409)

    # only trekkers can register. Admin and staff are made by the admin
    execute("INSERT INTO users (name, email, password, phone, role) VALUES (?, ?, ?, ?, 'trekker')",
            (name, email, generate_password_hash(password), phone))
    return jsonify(message="Registered successfully, please login"), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = query_one("SELECT * FROM users WHERE email=?", (email,))
    if user is None or not check_password_hash(user["password"], password):
        return error("Wrong email or password", 401)
    if user["status"] != "active":
        return error("Your account is " + user["status"] + ". Contact the admin.", 403)
    return jsonify(token=make_token(user["id"]), user=user_info(user))


@auth_bp.route("/me", methods=["PUT"])
@login_required()
def update_profile():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()

    if name == "" or not valid_email(email):
        return error("Enter a valid name and email")
    other = query_one("SELECT id FROM users WHERE email=? AND id != ?", (email, g.user["id"]))
    if other:
        return error("This email is used by someone else", 409)

    password = g.user["password"]
    if data.get("new_password"):
        if not check_password_hash(password, data.get("current_password") or ""):
            return error("Current password is wrong")
        if len(data["new_password"]) < 6:
            return error("New password must be at least 6 characters")
        password = generate_password_hash(data["new_password"])

    execute("UPDATE users SET name=?, email=?, phone=?, password=? WHERE id=?",
            (name, email, phone, password, g.user["id"]))
    user = query_one("SELECT * FROM users WHERE id=?", (g.user["id"],))
    return jsonify(user=user_info(user))
