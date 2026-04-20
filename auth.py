from flask import Blueprint, request, jsonify
from db import get_db
from flask_jwt_extended import create_access_token
import bcrypt

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO users(username,password)VALUES(%s,%s)",
            (username, hashed.decode("utf-8")),
        )
        db.commit()
        return jsonify({"message": "User registered successfully"})
    except:
        return jsonify({"error": "User already exists"}), 400


@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"error": "Invalid username"}), 401
    stored_password = user["password"].encode("utf-8")
    if not bcrypt.checkpw(password.encode("utf-8"), stored_password):
        return jsonify({"error": "Invalid password"}), 401
    token = create_access_token(identity=str(user["id"]))
    return jsonify({"token": token})
