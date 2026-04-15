import mysql.connector


def get_db():
    return mysql.connector.connect(
        host="localhost", user="root", password="Root123", database="url_project"
    )
