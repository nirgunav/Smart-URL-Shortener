import psycopg2
import os


def get_db():
    return psycopg2.connect("DATABASE_URL", sslmode="require")
