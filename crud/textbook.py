from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid


def bulk_save_chapters(db: Session, course_id: str, chapters: list):
    """Delete all existing chapters/topics for a course then re-insert from list."""
    # Delete existing topics first (FK constraint)
    existing = db.execute(
        text("SELECT id FROM chapters WHERE course_id = :cid"), {"cid": course_id}
    ).fetchall()
    for row in existing:
        db.execute(text("DELETE FROM topics WHERE chapter_id = :cid"), {"cid": row[0]})
    db.execute(text("DELETE FROM chapters WHERE course_id = :cid"), {"cid": course_id})

    for idx, chapter in enumerate(chapters):
        chid = f"ch{uuid.uuid4().hex[:8]}"
        db.execute(
            text("INSERT INTO chapters (id, title, summary, course_id) VALUES (:id, :title, :summary, :cid)"),
            {"id": chid, "title": chapter.get("title", ""), "summary": chapter.get("summary", ""), "cid": course_id},
        )
        for tidx, topic in enumerate(chapter.get("topics", [])):
            tid = f"t{uuid.uuid4().hex[:8]}"
            db.execute(
                text(
                    "INSERT INTO topics (id, title, description, chapter_id, `order`) "
                    "VALUES (:id, :title, :desc, :chid, :ord)"
                ),
                {"id": tid, "title": topic.get("title", ""), "desc": topic.get("description", ""), "chid": chid, "ord": tidx},
            )
    db.commit()


def save_grading_components(db: Session, course_id: str, components: list):
    """Replace grading components for a course."""
    db.execute(text("DELETE FROM grading_components WHERE course_id = :cid"), {"cid": course_id})
    for comp in components:
        gid = f"g{uuid.uuid4().hex[:8]}"
        db.execute(
            text(
                "INSERT INTO grading_components (id, course_id, name, weight, component_type) "
                "VALUES (:id, :cid, :name, :weight, :type)"
            ),
            {"id": gid, "cid": course_id, "name": comp.get("name", ""), "weight": comp.get("weight", 0), "type": comp.get("component_type", "assessment")},
        )
    db.commit()


def get_grading_components(db: Session, course_id: str):
    rows = db.execute(
        text("SELECT id, course_id, name, weight, component_type FROM grading_components WHERE course_id = :cid"),
        {"cid": course_id},
    ).fetchall()
    return [{"id": r[0], "course_id": r[1], "name": r[2], "weight": r[3], "component_type": r[4]} for r in rows]


def save_semester_plan(db: Session, course_id: str, weeks: list):
    """Replace semester plan for a course."""
    db.execute(text("DELETE FROM semester_weeks WHERE course_id = :cid"), {"cid": course_id})
    for week in weeks:
        wid = f"w{uuid.uuid4().hex[:8]}"
        db.execute(
            text(
                "INSERT INTO semester_weeks (id, course_id, week_num, chapter_title, topics_json, notes) "
                "VALUES (:id, :cid, :wnum, :ctitle, :tjson, :notes)"
            ),
            {
                "id": wid, "cid": course_id,
                "wnum": week.get("week_num", 0),
                "ctitle": week.get("chapter_title", ""),
                "tjson": week.get("topics_json", "[]"),
                "notes": week.get("notes", ""),
            },
        )
    db.commit()


def get_semester_plan(db: Session, course_id: str):
    rows = db.execute(
        text(
            "SELECT id, course_id, week_num, chapter_title, topics_json, notes "
            "FROM semester_weeks WHERE course_id = :cid ORDER BY week_num"
        ),
        {"cid": course_id},
    ).fetchall()
    return [
        {"id": r[0], "course_id": r[1], "week_num": r[2], "chapter_title": r[3], "topics_json": r[4], "notes": r[5]}
        for r in rows
    ]
