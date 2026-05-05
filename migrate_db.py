import sqlite3

def migrate():
    conn = sqlite3.connect('c:/Users/Lenovo/Desktop/learnpulse/LearnPulseBackend/learnpulse.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE topics ADD COLUMN is_open BOOLEAN DEFAULT 0;")
        print("Added is_open to topics")
    except sqlite3.OperationalError as e:
        print(f"topics error: {e}")
        
    try:
        cursor.execute("ALTER TABLE chapters ADD COLUMN is_final_quiz_open BOOLEAN DEFAULT 0;")
        print("Added is_final_quiz_open to chapters")
    except sqlite3.OperationalError as e:
        print(f"chapters error: {e}")
        
    try:
        cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN points_awarded INTEGER DEFAULT 0;")
        print("Added points_awarded to quiz_attempts")
    except sqlite3.OperationalError as e:
        print(f"quiz_attempts error: {e}")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
