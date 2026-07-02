from flask import Blueprint, request, jsonify
from db import get_db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt

auth = Blueprint("auth", __name__)


# ---------------- REGISTER ----------------
@auth.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username & password required"}), 400

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
    if cursor.fetchone():
        return jsonify({"error": "User already exists"}), 400

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    cursor.execute(
        "INSERT INTO users(username,password) VALUES(%s,%s)",
        (username, hashed.decode()),
    )
    db.commit()

    return jsonify({"message": "User registered successfully"})


# ---------------- LOGIN ----------------
@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id, username, password FROM users WHERE username=%s", (username,)
    )
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 401

    user_id = user[0]
    stored_password = user[2].encode()

    if not bcrypt.checkpw(password.encode(), stored_password):
        return jsonify({"error": "Invalid password"}), 401

    token = create_access_token(identity=str(user_id))

    return jsonify({"token": token, "message": "Login successful", "user_id": user_id})


# ---------------- GET CURRENT USER ----------------
@auth.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id, username FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"id": user[0], "username": user[1]})


# ---------------- CHANGE PASSWORD ----------------
@auth.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.json

    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "Missing fields"}), 400

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT password FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    stored_password = user[0].encode()

    if not bcrypt.checkpw(old_password.encode(), stored_password):
        return jsonify({"error": "Old password incorrect"}), 401

    new_hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())

    cursor.execute(
        "UPDATE users SET password=%s WHERE id=%s", (new_hashed.decode(), user_id)
    )
    db.commit()

    return jsonify({"message": "Password updated successfully"})


# ---------------- DELETE ACCOUNT ----------------
@auth.route("/delete-account", methods=["DELETE"])
@jwt_required()
def delete_account():
    user_id = get_jwt_identity()

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()

    return jsonify({"message": "Account deleted"})


# ---------------- LOGOUT (CLIENT SIDE TOKEN REMOVE) ----------------
@auth.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    # JWT is stateless → logout handled in frontend
    return jsonify({"message": "Logout successful (remove token from frontend)"})


# ---------------- VALIDATE TOKEN ----------------
@auth.route("/validate", methods=["GET"])
@jwt_required()
def validate():
    user_id = get_jwt_identity()
    return jsonify({"valid": True, "user_id": user_id})
