from db import get_db

db = get_db()
cursor = db.cursor()
cursor.execute(
    """
ALTER TABLE urls
ADD COLUMN IF NOT EXISTS clicks INTEGER DEFAULT 0;
"""
)
db.commit()
cursor.close()
db.close()
print("Done")
