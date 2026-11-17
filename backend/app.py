from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
import config
from db import close_db, create_tables_and_admin

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.staff import staff_bp
from routes.trekker import trekker_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.teardown_appcontext(close_db)

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(trekker_bp)

# create the tables and the admin from code (no manual database work)
create_tables_and_admin()


@app.errorhandler(HTTPException)
def http_error(e):
    return jsonify(error=e.description), e.code


@app.errorhandler(Exception)
def server_error(e):
    print("ERROR:", e)
    return jsonify(error="Something went wrong"), 500


if __name__ == "__main__":
    app.run(debug=True, port=5050)
