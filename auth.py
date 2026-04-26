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
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, username, password FROM users WHERE username=%s", (username,)
        )
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Invalid username"}), 401
        user_id = user[0]
        stored_password = user[2]
        if not bcrypt.checkpw(password.encode("utf-8"), stored_password):
            return jsonify({"error": "Invalid password"}), 401
        token = create_access_token(identity=str(user[0]))
        return jsonify({"token": token})
    except Exception as e:
        print("LOGIN ERROR:", e)
    return jsonify({"error": "Server error"}), 500
