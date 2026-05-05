from sqlalchemy.orm import Session
from sqlalchemy import text
import schemas
import uuid

def create_chapter(db: Session, course_id: str, data: schemas.ChapterCreate):
    chid = f"ch{uuid.uuid4().hex[:8]}"
    db.execute(text("INSERT INTO chapters (id, title, summary, course_id) VALUES (:id, :t, :s, :c)"),
               {"id": chid, "t": data.title, "s": data.summary, "c": course_id})
    db.commit()
    return db.execute(text("SELECT * FROM chapters WHERE id=:id"), {"id": chid}).fetchone()

def update_chapter(db: Session, chapter_id: str, data: schemas.ChapterUpdate):
    updates = []
    params = {"id": chapter_id}
    if data.title is not None:
        updates.append("title = :t"); params["t"] = data.title
    if data.summary is not None:
        updates.append("summary = :s"); params["s"] = data.summary
    if hasattr(data, 'is_final_quiz_open') and data.is_final_quiz_open is not None:
        updates.append("is_final_quiz_open = :ifo"); params["ifo"] = 1 if data.is_final_quiz_open else 0
    if updates:
        db.execute(text(f"UPDATE chapters SET {', '.join(updates)} WHERE id=:id"), params)
        db.commit()
    return db.execute(text("SELECT * FROM chapters WHERE id=:id"), {"id": chapter_id}).fetchone()

def delete_chapter(db: Session, chapter_id: str):
    res = db.execute(text("SELECT * FROM chapters WHERE id=:id"), {"id": chapter_id}).fetchone()
    if res:
        db.execute(text("DELETE FROM chapters WHERE id=:id"), {"id": chapter_id})
        db.commit()
    return res

def create_topic(db: Session, chapter_id: str, data: schemas.TopicCreate):
    c = db.execute(text("SELECT COUNT(*) as c FROM topics WHERE chapter_id=:id"), {"id": chapter_id}).fetchone()
    order = c.c if c else 0
    tid = f"t{uuid.uuid4().hex[:8]}"
    db.execute(text("INSERT INTO topics (id, title, description, chapter_id, `order`) VALUES (:id, :t, :d, :c, :o)"),
               {"id": tid, "t": data.title, "d": data.description, "c": chapter_id, "o": order})
    db.commit()
    return db.execute(text("SELECT * FROM topics WHERE id=:id"), {"id": tid}).fetchone()

def update_topic(db: Session, topic_id: str, data: schemas.TopicUpdate):
    updates = []
    params = {"id": topic_id}
    if data.title is not None:
        updates.append("title = :t"); params["t"] = data.title
    if data.description is not None:
        updates.append("description = :d"); params["d"] = data.description
    if hasattr(data, 'is_open') and data.is_open is not None:
        updates.append("is_open = :io"); params["io"] = 1 if data.is_open else 0
    if updates:
        db.execute(text(f"UPDATE topics SET {', '.join(updates)} WHERE id=:id"), params)
        db.commit()
    return db.execute(text("SELECT * FROM topics WHERE id=:id"), {"id": topic_id}).fetchone()

def get_topic(db: Session, topic_id: str):
    return db.execute(text("SELECT * FROM topics WHERE id=:id"), {"id": topic_id}).fetchone()

def delete_topic(db: Session, topic_id: str):
    res = db.execute(text("SELECT * FROM topics WHERE id=:id"), {"id": topic_id}).fetchone()
    if res:
        db.execute(text("DELETE FROM topic_completions WHERE topic_id=:id"), {"id": topic_id})
        db.execute(text("DELETE FROM topics WHERE id=:id"), {"id": topic_id})
        db.commit()
    return res

def mark_topic_completed(db: Session, user_id: str, topic_id: str):
    res = db.execute(text("SELECT * FROM topic_completions WHERE user_id=:u AND topic_id=:t"),
                     {"u": user_id, "t": topic_id}).fetchone()
    if not res:
        db.execute(text("INSERT INTO topic_completions (user_id, topic_id) VALUES (:u, :t)"),
                   {"u": user_id, "t": topic_id})
        
        course_id = db.execute(text("""
            SELECT ch.course_id FROM topics t
            JOIN chapters ch ON ch.id = t.chapter_id
            WHERE t.id = :tid
        """), {"tid": topic_id}).scalar()
        
        if course_id:
            from .users import award_course_points
            award_course_points(db, user_id, course_id, 10)
        db.commit()
