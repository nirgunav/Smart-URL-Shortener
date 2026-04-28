import psycopg2
import os
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://url_db_2yjn_user:0yiwgAX9ebtpf9bXY9XlCGElKoKQbwIy@dpg-d7n110hkh4rs73auv8cg-a.oregon-postgres.render.com/url_db_2yjn"


def get_db():
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise Exception("DATABASE_URL not found")

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
