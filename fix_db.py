import sqlite3
conn = sqlite3.connect('learnpulse.db')
cursor = conn.cursor()
try:
    cursor.execute('ALTER TABLE courses ADD COLUMN category TEXT DEFAULT "General"')
    print("Added category column")
except Exception as e:
    print(f"Error adding category: {e}")

try:
    cursor.execute('ALTER TABLE courses ADD COLUMN image TEXT DEFAULT ""')
    print("Added image column")
except Exception as e:
    print(f"Error adding image: {e}")

conn.commit()
conn.close()
