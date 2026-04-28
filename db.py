import psycopg2
import os
from psycopg2.extras import RealDictCursor


def get_db():
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise Exception("DATABASE_URL not found")

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
