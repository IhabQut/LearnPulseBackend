from sqlalchemy.orm import Session
from sqlalchemy import text
import schemas
import uuid
import datetime

def create_meeting_request(db: Session, user_id: str, data: schemas.MeetingRequestCreate):
    mid = f"m{uuid.uuid4().hex[:8]}"
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    db.execute(text("""
        INSERT INTO meeting_requests (id, user_id, professor_id, note, slot, meeting_type, status, date)
        VALUES (:id, :u, :p, :n, :s, :t, 'pending', :d)
    """), {"id": mid, "u": user_id, "p": data.professor_id, "n": data.note, 
           "s": data.slot, "t": data.meeting_type, "d": dt})
    db.commit()
    return db.execute(text("SELECT * FROM meeting_requests WHERE id=:id"), {"id": mid}).fetchone()

def get_meeting_requests(db: Session, user_id: str):
    return db.execute(text("""
        SELECT * FROM meeting_requests WHERE user_id=:u OR professor_id=:u
    """), {"u": user_id}).fetchall()

def update_meeting_status(db: Session, meeting_id: str, status: str):
    db.execute(text("UPDATE meeting_requests SET status=:s WHERE id=:id"), {"s": status, "id": meeting_id})
    db.commit()
    return db.execute(text("SELECT * FROM meeting_requests WHERE id=:id"), {"id": meeting_id}).fetchone()
