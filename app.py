from flask import Flask, render_template, request, redirect, jsonify
from db import get_db
import random, string
from datetime import datetime
import qrcode
import os

from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from auth import auth

BASE_URL = "https://smart-url-shortener-74yd.onrender.com"

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["JWT_SECRET_KEY"] = "mysecretkey"

jwt = JWTManager(app)
app.register_blueprint(auth)


# ---------------- DB ----------------
def create_tables():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE,
        password VARCHAR(255)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        id INT AUTO_INCREMENT PRIMARY KEY,
        original_url TEXT,
        short_code VARCHAR(50) UNIQUE,
        expiry DATETIME,
        one_time INT,
        cclicks INT DEFAULT 0,
        last_opened DATETIME,
        visitor_ip TEXT,
        browser TEXT,
        user_id INT,
        risk_level VARCHAR(30),
        score INT,
        reasons TEXT
    )
    """)

    db.commit()
    cursor.close()
    db.close()


create_tables()


# ---------------- HELPERS ----------------
def generate_code():
    return "".join(random.choices(string.ascii_letters + string.digits, k=6))


def ai_risk(url):
    score = 0
    reasons = []

    risky_words = ["login", "bank", "verify", "free", "password", "account"]

    for word in risky_words:
        if word in url.lower():
            score += 2
            reasons.append(f"Contains suspicious word: {word}")

    if sum(c.isdigit() for c in url) > 5:
        score += 1
        reasons.append("Too many numbers")

    if "https" not in url:
        score += 1
        reasons.append("Not secure (no HTTPS)")

    if score >= 4:
        return "Dangerous", score, reasons
    elif score >= 2:
        return "Suspicious", score, reasons
    else:
        return "Safe", score, reasons


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------------- SHORTEN ----------------
@app.route("/api/shorten", methods=["POST"])
@jwt_required()
def shorten():
    user_id = get_jwt_identity()
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL required"}), 400

    db = get_db()
    cursor = db.cursor()

    code = generate_code()

    risk_level, score, reasons = ai_risk(url)

    cursor.execute(
        """
        INSERT INTO urls (original_url, short_code, user_id, risk_level, score, reasons)
        VALUES (%s,%s,%s,%s,%s,%s)
    """,
        (url, code, user_id, risk_level, score, ",".join(reasons)),
    )

    db.commit()

    return jsonify(
        {
            "short_url": f"{BASE_URL}/{code}",
            "risk_level": risk_level,
            "score": score,
            "reasons": reasons,
            "clicks": 0,
            "last_opened": "Never",
        }
    )


# ---------------- DELETE ----------------
@app.route("/api/delete/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_url(id):
    user_id = get_jwt_identity()

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM urls WHERE id=%s AND user_id=%s", (id, user_id))

    db.commit()
    return jsonify({"message": "Deleted"})


# ---------------- REDIRECT ----------------
@app.route("/<code>")
def redirect_url(code):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT original_url FROM urls WHERE short_code=%s", (code,))
    result = cursor.fetchone()

    if not result:
        return "Not Found", 404

    return redirect(result[0])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
