from sqlalchemy.orm import Session
from sqlalchemy import text
import schemas
import uuid
from typing import List

def create_notification(db: Session, data: schemas.NotificationCreate):
    nid = f"n_{uuid.uuid4().hex[:8]}"
    db.execute(text("""
        INSERT INTO notifications (id, user_id, title, message, type, is_read, date)
        VALUES (:id, :u, :t, :m, :ty, 0, :d)
    """), {"id": nid, "u": data.user_id, "t": data.title, "m": data.message, "ty": data.type, "d": data.date})
    db.commit()
    return db.execute(text("SELECT * FROM notifications WHERE id=:id"), {"id": nid}).fetchone()

def get_notifications(db: Session, user_id: str):
    return db.execute(text("SELECT * FROM notifications WHERE user_id=:u ORDER BY date DESC"), {"u": user_id}).fetchall()

def mark_notification_read(db: Session, notification_id: str):
    db.execute(text("UPDATE notifications SET is_read=1 WHERE id=:id"), {"id": notification_id})
    db.commit()
    return db.execute(text("SELECT * FROM notifications WHERE id=:id"), {"id": notification_id}).fetchone()

def delete_notification(db: Session, notification_id: str):
    res = db.execute(text("SELECT * FROM notifications WHERE id=:id"), {"id": notification_id}).fetchone()
    if res:
        db.execute(text("DELETE FROM notifications WHERE id=:id"), {"id": notification_id})
        db.commit()
    return res
