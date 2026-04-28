from flask import Flask, render_template, request, redirect, jsonify
from db import get_db
import random, string
from datetime import datetime, timedelta
import qrcode
from PIL import Image
import os
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from auth import auth

BASE_URL = "https://smart-url-shortener-74yd.onrender.com"

app = Flask(__name__)


@app.route("/test")
def test():
    return "Server working"


def create_tables():
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """ 
                   CREATE TABLE IF NOT EXISTS users (
                   id SERIAL PRIMARY KEY,
                   username TEXT UNIQUE,
                   password TEXT
                   );
                   """
    )
    cursor.execute(
        """
                   CREATE TABLE IF NOT EXISTS urls (
                   id SERIAL PRIMARY KEY,
                   original_url TEXT,
                   short_code TEXT UNIQUE,
                   expiry TIMESTAMP,
                   password TEXT,
                   one_time INTEGER,
                   cclicks INTEGER DEFAULT 0,
                   last_opened TIMESTAMP,
                   user_id INTEGER,
                   risk_level TEXT,
                   score INTEGER,
                   reasons TEXT
                   );
                   """
    )
    db.commit()
    cursor.close()
    db.close()


create_tables()


app.config["JWT_SECRET_KEY"] = "super-secret-key-very-long-at-least-32-characters"
jwt = JWTManager(app)
app.register_blueprint(auth)

QR_FOLDER = "static/qr"
os.makedirs(QR_FOLDER, exist_ok=True)


def generate_qr(url, code):
    img = qrcode.make(url)
    qr_path = f"{QR_FOLDER}/{code}.png"
    img.save(qr_path)
    return qr_path


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
    digit_count = sum(c.isdigit() for c in url)
    if digit_count > 5:
        score += 1
        reasons.append("Too many numbers in URL")
    if "https" not in url:
        score += 1
        reasons.append("Missing HTTPS pattern,Not Secure")
    if score >= 4:
        return "Dangerous", score, reasons
    elif score >= 2:
        return "Suspicious", score, reasons
    else:
        return "Safe", score, reasons


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/<code>")
def redirect_url(code):
    try:

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT original_url, expiry, password, one_time, cclicks
            FROM urls
            WHERE short_code=%s
            """,
            (code,),
        )
        result = cursor.fetchone()
        if not result:
            return "<h2> Link Not Found</h2>", 404
        original_url = result[0]
        if not original_url.startswith("http://") and not original_url.startswith(
            "https://"
        ):
            original_url = "https://" + original_url
        cursor.execute(
            """
            UPDATE urls 
            SET cclicks = cclicks + 1,
                last_opened = NOW()
            WHERE short_code=%s
            """,
            (code,),
        )
        db.commit()
        print("REDIRECTING TO:", original_url)
        return redirect(original_url)
    except Exception as e:
        print("REDIRECT ERROR:", repr(e))
        return f"<h2>Server Error: {str(e)}</h2>", 500


@app.route("/dashboard")
@jwt_required()
def dashboard():
    user_id = get_jwt_identity()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM urls WHERE user_id=%s ORDER BY id DESC", (user_id,))
    links = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS total FROM urls")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(cclicks) AS clicks FROM urls")
    clicks = cursor.fetchone()[0]
    return render_template("dashboard.html", links=links, total=total, clicks=clicks)


@app.route("/api/delete/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_url(id):
    user_id = get_jwt_identity()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM urls WHERE id=%s AND user_id=%s", (id, user_id))
    db.commit()
    return jsonify({"message": "Deleted"})


@app.route("/api/shorten", methods=["POST"])
@jwt_required()
def shorten():
    user_id = get_jwt_identity()
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT short_code FROM urls WHERE original_url=%s", (url,))
    existing = cursor.fetchone()
    if existing:
        risk_level, score, reasons = ai_risk(url)
        return jsonify(
            {
                "short_url": f"{BASE_URL}/{existing[0]}",
                "message": "Already Shortened before",
                "qr": f"/static/qr/{existing[0]}.png",
                "risk_level": risk_level,
                "score": score,
                "reasons": reasons,
                "clicks": 0,
                "last_opened": "Already exists",
            }
        )
    custom = data.get("custom")
    password = data.get("password")
    expiry = data.get("expiry")
    one_time = 1 if data.get("one_time") else 0
    if expiry and expiry.strip():
        expiry = datetime.strptime(expiry, "%Y-%m-%d")
    else:
        expiry = None

    risk_level, score, reasons = ai_risk(url)
    if risk_level == "Dangerous":
        return jsonify({"error": "Blocked dangerous URL"})
    code = custom if custom else generate_code()
    cursor.execute("SELECT id FROM urls WHERE short_code=%s", (code,))
    if cursor.fetchone():
        code = generate_code()
    cursor.execute(
        """
        INSERT INTO urls (original_url, short_code, expiry, password, one_time,user_id, risk_level, score, reasons) 
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,
        (
            url,
            code,
            expiry,
            password,
            one_time,
            user_id,
            risk_level,
            score,
            ",".join(reasons),
        ),
    )
    db.commit()
    short_url = f"{BASE_URL}/{code}"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(short_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    logo_path = "static/logo.png"
    if os.path.exists(logo_path):
        logo = Image.open("static/logo.png").convert("RGBA")
        qr_w, qr_h = img.size
        logo_size = qr_w // 4
        logo = logo.resize((logo_size, logo_size))
        pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        img.paste(logo, pos, mask=logo)
    qr_path = f"{QR_FOLDER}/{code}.png"
    img.save(qr_path)
    return jsonify(
        {
            "short_url": f"{BASE_URL}/{code}",
            "qr": f"/{qr_path}",
            "risk_level": risk_level,
            "score": score,
            "reasons": reasons,
            "clicks": 0,
            "last_opened": "Not opened yet",
        }
    )


if __name__ == "__main__":
    create_tables()
    app.run(host="0.0.0.0", port=10000)
