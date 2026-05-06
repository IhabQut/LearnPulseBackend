from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import json

def save_course_textbook(db: Session, course_id: str, data: dict):
    tid = f"tx{uuid.uuid4().hex[:8]}"
    db.execute(
        text("INSERT INTO course_textbooks (id, course_id, filename, file_type, status) VALUES (:id, :cid, :fname, :ftype, :st)"),
        {"id": tid, "cid": course_id, "fname": data.get("filename", ""), "ftype": data.get("file_type", ""), "st": data.get("status", "done")}
    )
    db.commit()

def bulk_save_chapters(db: Session, course_id: str, chapters: list):
    """Delete all existing chapters/topics for a course then re-insert using raw SQL."""
    # Delete existing topics first (FK constraint)
    existing = db.execute(
        text("SELECT id FROM chapters WHERE course_id = :cid"), {"cid": course_id}
    ).fetchall()
    for row in existing:
        db.execute(text("DELETE FROM topics WHERE chapter_id = :chid"), {"chid": row[0]})
    db.execute(text("DELETE FROM chapters WHERE course_id = :cid"), {"cid": course_id})
    
    for idx, chapter_data in enumerate(chapters):
        chid = f"ch{uuid.uuid4().hex[:8]}"
        db.execute(
            text("INSERT INTO chapters (id, title, summary, course_id) VALUES (:id, :title, :summary, :cid)"),
            {"id": chid, "title": chapter_data.get("title", ""), "summary": chapter_data.get("summary", ""), "cid": course_id}
        )
        
        for tidx, topic_data in enumerate(chapter_data.get("topics", [])):
            tid = f"t{uuid.uuid4().hex[:8]}"
            db.execute(
                text("INSERT INTO topics (id, title, description, chapter_id, `order`) VALUES (:id, :title, :desc, :chid, :ord)"),
                {"id": tid, "title": topic_data.get("title", ""), "desc": topic_data.get("description", ""), "chid": chid, "ord": tidx}
            )
    db.commit()

def save_grading_components(db: Session, course_id: str, components: list):
    """Replace grading components for a course using raw SQL."""
    db.execute(text("DELETE FROM grading_components WHERE course_id = :cid"), {"cid": course_id})
    for comp in components:
        gid = f"g{uuid.uuid4().hex[:8]}"
        db.execute(
            text("INSERT INTO grading_components (id, course_id, name, weight, component_type) VALUES (:id, :cid, :name, :weight, :type)"),
            {"id": gid, "cid": course_id, "name": comp.get("name", ""), "weight": comp.get("weight", 0), "type": comp.get("component_type", "assessment")}
        )
    db.commit()

def get_grading_components(db: Session, course_id: str):
    rows = db.execute(
        text("SELECT id, course_id, name, weight, component_type FROM grading_components WHERE course_id = :cid"),
        {"cid": course_id}
    ).fetchall()
    return [{"id": r[0], "course_id": r[1], "name": r[2], "weight": r[3], "component_type": r[4]} for r in rows]

def save_semester_plan(db: Session, course_id: str, weeks: list):
    """Replace semester plan and week topics for a course using raw SQL."""
    # Delete existing week topics first
    existing_weeks = db.execute(
        text("SELECT id FROM semester_weeks WHERE course_id = :cid"), {"cid": course_id}
    ).fetchall()
    for row in existing_weeks:
        db.execute(text("DELETE FROM semester_week_topics WHERE week_id = :wid"), {"wid": row[0]})
    db.execute(text("DELETE FROM semester_weeks WHERE course_id = :cid"), {"cid": course_id})
    
    for week in weeks:
        wid = f"w{uuid.uuid4().hex[:8]}"
        db.execute(
            text("INSERT INTO semester_weeks (id, course_id, week_num, chapter_title, notes) VALUES (:id, :cid, :wnum, :ctitle, :notes)"),
            {"id": wid, "cid": course_id, "wnum": week.get("week_num", 0), "ctitle": week.get("chapter_title", ""), "notes": week.get("notes", "")}
        )
        
        # week topics
        topics = week.get("topics", [])
        for topic in topics:
            wtid = f"wt{uuid.uuid4().hex[:8]}"
            db.execute(
                text("INSERT INTO semester_week_topics (id, week_id, title) VALUES (:id, :wid, :title)"),
                {"id": wtid, "wid": wid, "title": topic.get("title", "")}
            )
    db.commit()

def get_semester_plan(db: Session, course_id: str):
    rows = db.execute(
        text("SELECT id, course_id, week_num, chapter_title, notes FROM semester_weeks WHERE course_id = :cid ORDER BY week_num"),
        {"cid": course_id}
    ).fetchall()
    
    result = []
    for r in rows:
        wid = r[0]
        topic_rows = db.execute(
            text("SELECT title FROM semester_week_topics WHERE week_id = :wid"), {"wid": wid}
        ).fetchall()
        result.append({
            "id": wid, "course_id": r[1], "week_num": r[2], "chapter_title": r[3], "notes": r[4],
            "topics": [{"title": tr[0]} for tr in topic_rows]
        })
    return result
