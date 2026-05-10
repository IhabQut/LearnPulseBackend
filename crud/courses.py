from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import uuid
import datetime
import schemas
import security
import models


# ---------------------------------------------------------------------------
# Small focused helpers — each fetches exactly one thing
# ---------------------------------------------------------------------------

def _fetch_course_rows(db: Session, user_id: str, enrolled_only: bool):
    """Return base course rows (one per course)."""
    enrollment_join = ""
    if enrolled_only:
        enrollment_join = (
            "JOIN enrollments e ON e.course_id = c.id "
            "AND e.user_id = :user_id AND e.status = 'approved'"
        )

    query = text(f"""
        SELECT
            c.id,
            c.title,
            c.description,
            c.owner_id,
            c.category,
            c.image,
            CASE WHEN c.is_open IS NULL THEN 1 ELSE c.is_open END AS is_open,
            u.name AS professor_name,
            (
                SELECT COUNT(*)
                FROM enrollments e2
                WHERE e2.course_id = c.id AND e2.status = 'approved'
            ) AS student_count
        FROM courses c
        {enrollment_join}
        LEFT JOIN users u ON u.id = c.owner_id
        ORDER BY c.id
    """)
    return db.execute(query, {"user_id": user_id or ""}).fetchall()


def _fetch_chapters(db: Session, course_id: str):
    """Return all chapters for a single course."""
    query = text("""
        SELECT
            id,
            title,
            summary,
            COALESCE(is_final_quiz_open, 0) AS is_final_quiz_open
        FROM chapters
        WHERE course_id = :cid
        ORDER BY id
    """)
    return db.execute(query, {"cid": course_id}).fetchall()


def _fetch_topics(db: Session, chapter_id: str, user_id: str):
    """Return all topics for a single chapter, including completion status."""
    query = text("""
        SELECT
            t.id,
            t.title,
            t.description,
            t.`order`,
            COALESCE(t.is_open, 0) AS is_open,
            tc.user_id AS completed_by
        FROM topics t
        LEFT JOIN topic_completions tc
            ON tc.topic_id = t.id AND tc.user_id = :user_id
        WHERE t.chapter_id = :chid
        ORDER BY t.`order`
    """)
    return db.execute(query, {"chid": chapter_id, "user_id": user_id or ""}).fetchall()


def _fetch_materials(db: Session, course_id: str):
    """Return all materials for a single course."""
    query = text("""
        SELECT id, name, type, url
        FROM materials
        WHERE course_id = :cid
    """)
    return db.execute(query, {"cid": course_id}).fetchall()


def _fetch_syllabus(db: Session, course_id: str) -> Optional[dict]:
    """Return the syllabus dict for a course, or None if missing."""
    row = db.execute(
        text("SELECT * FROM course_syllabi WHERE course_id = :cid"),
        {"cid": course_id}
    ).fetchone()
    if not row:
        return None

    sid = row[0]
    objectives     = db.execute(text("SELECT text FROM syllabus_objectives WHERE syllabus_id = :sid"), {"sid": sid}).fetchall()
    textbooks      = db.execute(text("SELECT title, author FROM syllabus_textbooks WHERE syllabus_id = :sid"), {"sid": sid}).fetchall()
    outcomes       = db.execute(text("SELECT text FROM syllabus_outcomes WHERE syllabus_id = :sid"), {"sid": sid}).fetchall()

    return {
        "id": row[0], "course_id": row[1], "course_code": row[2] or "",
        "semester": row[3] or "", "instructor_name": row[4] or "",
        "instructor_email": row[5] or "", "instructor_phone": row[6] or "",
        "office_hours": row[7] or "", "class_time_location": row[8] or "",
        "zoom_link": row[9] or "", "description": row[10] or "",
        "objectives":       [{"text": o[0]} for o in objectives],
        "textbooks":        [{"title": t[0], "author": t[1]} for t in textbooks],
        "learning_outcomes":[{"text": o[0]} for o in outcomes],
    }


def _build_chapters(db: Session, course_id: str, user_id: str) -> list:
    """Assemble chapter + topic list for a course."""
    chapters = []
    for ch in _fetch_chapters(db, course_id):
        topics = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "order": t.order,
                "is_open": bool(t.is_open),
                "completed": (t.completed_by is not None),
            }
            for t in _fetch_topics(db, ch.id, user_id)
        ]
        chapters.append({
            "id": ch.id,
            "title": ch.title,
            "summary": ch.summary,
            "is_final_quiz_open": bool(ch.is_final_quiz_open),
            "topics": topics,
        })
    return chapters


def _build_course_obj(db: Session, row, user_id: str) -> schemas.Course:
    """Build a full Course schema object from a base course row."""
    cid = row.id

    chapters  = _build_chapters(db, cid, user_id)
    materials = [
        {"id": m.id, "name": m.name, "type": m.type, "url": m.url, "course_id": cid}
        for m in _fetch_materials(db, cid)
    ]
    syllabus  = _fetch_syllabus(db, cid)
    user_role = security.get_course_role(db, user_id, cid) if user_id else None

    return schemas.Course.model_validate({
        "id":             cid,
        "title":          row.title,
        "description":    row.description,
        "professor_id":   row.owner_id,
        "professor_name": row.professor_name or "",
        "student_count":  row.student_count or 0,
        "is_open":        bool(row.is_open),
        "category":       row.category or "General",
        "image":          row.image or "",
        "user_role":      user_role,
        "chapters":       chapters,
        "materials":      materials,
        "syllabus":       syllabus,
    })


# ---------------------------------------------------------------------------
# Public CRUD functions
# ---------------------------------------------------------------------------

def get_courses(db: Session, user_id: str = "", enrolled_only: bool = False) -> List[schemas.Course]:
    rows = _fetch_course_rows(db, user_id, enrolled_only)
    return [_build_course_obj(db, row, user_id) for row in rows]


def get_course(db: Session, course_id: str, user_id: str = "") -> Optional[schemas.Course]:
    row = db.execute(
        text("SELECT c.id, c.title, c.description, c.owner_id, c.category, c.image, "
             "CASE WHEN c.is_open IS NULL THEN 1 ELSE c.is_open END AS is_open, "
             "u.name AS professor_name, "
             "(SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id AND e.status = 'approved') AS student_count "
             "FROM courses c LEFT JOIN users u ON u.id = c.owner_id "
             "WHERE c.id = :cid"),
        {"cid": course_id}
    ).fetchone()
    if not row:
        return None
    return _build_course_obj(db, row, user_id)


def create_course(db: Session, data: schemas.CourseCreate, owner_id: str):
    cid = f"c{uuid.uuid4().hex[:8]}"
    db.execute(
        text("INSERT INTO courses (id, title, description, category, image, owner_id, is_open) "
             "VALUES (:id, :title, :desc, :cat, :img, :owner, 1)"),
        {"id": cid, "title": data.title, "desc": data.description,
         "cat": data.category or "General", "img": data.image or "", "owner": owner_id}
    )

    # Auto-enroll the creator as owner
    eid = f"e{uuid.uuid4().hex[:8]}"
    db.execute(
        text("INSERT INTO enrollments (id, user_id, course_id, status, role, date) "
             "VALUES (:id, :u, :c, 'approved', 'owner', :d)"),
        {"id": eid, "u": owner_id, "c": cid, "d": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    )

    db.commit()
    return get_course(db, cid)


def update_course(db: Session, course_id: str, data: schemas.CourseUpdate):
    updates = []
    params  = {"id": course_id}

    if data.title       is not None: updates.append("title = :title");       params["title"]   = data.title
    if data.description is not None: updates.append("description = :desc");  params["desc"]    = data.description
    if data.is_open     is not None: updates.append("is_open = :is_open");   params["is_open"] = data.is_open
    if data.category    is not None: updates.append("category = :cat");      params["cat"]     = data.category
    if data.image       is not None: updates.append("image = :img");         params["img"]     = data.image

    if updates:
        db.execute(text(f"UPDATE courses SET {', '.join(updates)} WHERE id = :id"), params)
        db.commit()

    return get_course(db, course_id)


def delete_course(db: Session, course_id: str):
    course = db.execute(text("SELECT * FROM courses WHERE id = :id"), {"id": course_id}).fetchone()
    if course:
        db.execute(text("DELETE FROM courses WHERE id = :id"), {"id": course_id})
        db.commit()
    return course


# ---------------------------------------------------------------------------
# Syllabus helpers
# ---------------------------------------------------------------------------

def get_syllabus(db: Session, course_id: str) -> Optional[dict]:
    return _fetch_syllabus(db, course_id)


def save_syllabus(db: Session, course_id: str, data: schemas.CourseSyllabusCreate):
    existing = db.execute(
        text("SELECT id FROM course_syllabi WHERE course_id = :cid"),
        {"cid": course_id}
    ).fetchone()

    if existing:
        sid = existing[0]
        db.execute(
            text("UPDATE course_syllabi SET "
                 "course_code=:cc, semester=:sem, instructor_name=:in, "
                 "instructor_email=:ie, instructor_phone=:ip, "
                 "office_hours=:oh, class_time_location=:ctl, "
                 "zoom_link=:zl, description=:desc "
                 "WHERE id = :sid"),
            {"cc": data.course_code, "sem": data.semester, "in": data.instructor_name,
             "ie": data.instructor_email, "ip": data.instructor_phone,
             "oh": data.office_hours, "ctl": data.class_time_location,
             "zl": data.zoom_link, "desc": data.description, "sid": sid}
        )
        # Clear old normalized items before re-inserting
        db.execute(text("DELETE FROM syllabus_objectives WHERE syllabus_id = :sid"), {"sid": sid})
        db.execute(text("DELETE FROM syllabus_textbooks  WHERE syllabus_id = :sid"), {"sid": sid})
        db.execute(text("DELETE FROM syllabus_outcomes   WHERE syllabus_id = :sid"), {"sid": sid})
    else:
        sid = f"syl{uuid.uuid4().hex[:8]}"
        db.execute(
            text("INSERT INTO course_syllabi "
                 "(id, course_id, course_code, semester, instructor_name, instructor_email, "
                 "instructor_phone, office_hours, class_time_location, zoom_link, description) "
                 "VALUES (:id, :cid, :cc, :sem, :in, :ie, :ip, :oh, :ctl, :zl, :desc)"),
            {"id": sid, "cid": course_id, "cc": data.course_code, "sem": data.semester,
             "in": data.instructor_name, "ie": data.instructor_email, "ip": data.instructor_phone,
             "oh": data.office_hours, "ctl": data.class_time_location,
             "zl": data.zoom_link, "desc": data.description}
        )

    # Insert normalized child rows
    for obj in data.objectives:
        db.execute(
            text("INSERT INTO syllabus_objectives (id, syllabus_id, text) VALUES (:id, :sid, :t)"),
            {"id": f"obj{uuid.uuid4().hex[:8]}", "sid": sid, "t": obj.text}
        )
    for txt in data.textbooks:
        db.execute(
            text("INSERT INTO syllabus_textbooks (id, syllabus_id, title, author) VALUES (:id, :sid, :t, :a)"),
            {"id": f"txtb{uuid.uuid4().hex[:8]}", "sid": sid, "t": txt.title, "a": txt.author}
        )
    for out in data.learning_outcomes:
        db.execute(
            text("INSERT INTO syllabus_outcomes (id, syllabus_id, text) VALUES (:id, :sid, :t)"),
            {"id": f"out{uuid.uuid4().hex[:8]}", "sid": sid, "t": out.text}
        )

    db.commit()
    return get_syllabus(db, course_id)
