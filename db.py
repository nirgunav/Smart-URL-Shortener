import psycopg2
import os

DATABASE_URL = "postgresql://url_db_2yjn_user:0yiwgAX9ebtpf9bXY9XlCGElKoKQbwIy@dpg-d7n110hkh4rs73auv8cg-a.oregon-postgres.render.com/url_db_2yjn"


def get_db():
    db_url = os.getenv("url-db")

    if db_url:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(
        host="dpg-d7n110hkh4rs73auv8cg-a",
        database="url-db",
        user="url_db_2yjn_user",
        password="0yiwgAX9ebtpf9bXY9XlCGElKoKQbwIy",
    )
