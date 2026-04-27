"""
One-time migration: add password_hash column and unique email index to existing SQLite database.
Safe to run multiple times -- checks if column/index already exist.
"""
import sqlite3

DB_PATH = "./learnpulse.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    # Add password_hash column if missing
    if "password_hash" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
        print("[OK] Added 'password_hash' column to users table.")
    else:
        print("[INFO] 'password_hash' column already exists.")

    # Make email non-null (update empty emails to be unique placeholders)
    cursor.execute("SELECT id, email FROM users WHERE email IS NULL OR email = ''")
    rows = cursor.fetchall()
    for user_id, email in rows:
        placeholder = f"{user_id}@placeholder.learnpulse.local"
        cursor.execute("UPDATE users SET email = ? WHERE id = ?", (placeholder, user_id))
        print(f"  -> Set placeholder email for user '{user_id}': {placeholder}")

    # Create unique index on email if it doesn't exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_users_email_unique'")
    if not cursor.fetchone():
        try:
            cursor.execute("CREATE UNIQUE INDEX ix_users_email_unique ON users(email)")
            print("[OK] Created unique index on users.email.")
        except sqlite3.IntegrityError as e:
            print(f"[WARN] Could not create unique index (duplicate emails exist): {e}")
    else:
        print("[INFO] Unique index on email already exists.")

    conn.commit()
    conn.close()
    print("\n[DONE] Migration complete!")

if __name__ == "__main__":
    migrate()
