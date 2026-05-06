from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import uuid
import schemas
import security
import models

def get_courses(db: Session, user_id: str = "", enrolled_only: bool = False) -> List[schemas.Course]:
    enrollment_filter = ""
    if enrolled_only:
        enrollment_filter = "JOIN enrollments e ON e.course_id = c.id AND e.user_id = :user_id AND e.status = 'approved'"

    query = text(f"""
        SELECT 
            c.id AS course_id, c.title AS course_title, c.description AS course_desc, c.owner_id,
            c.category AS course_category, c.image AS course_image,
            CASE WHEN c.is_open IS NULL THEN 1 ELSE c.is_open END AS course_is_open,
            u.name AS professor_name,
            (SELECT COUNT(*) FROM enrollments e2 WHERE e2.course_id = c.id AND e2.status = 'approved') AS student_count,
            ch.id AS chapter_id, ch.title AS chapter_title, ch.summary AS chapter_summary, COALESCE(ch.is_final_quiz_open, 0) AS chapter_is_final_quiz_open,
            t.id AS topic_id, t.title AS topic_title, t.description AS topic_desc, t.`order` AS topic_order, COALESCE(t.is_open, 0) AS topic_is_open,
            tc.user_id AS completed_by,
            m.id AS mat_id, m.name AS mat_name, m.type AS mat_type, m.url AS mat_url,
            sy.id AS syl_id, sy.course_code, sy.semester, sy.instructor_name, sy.instructor_email, sy.instructor_phone,
            sy.office_hours, sy.class_time_location, sy.zoom_link, sy.description AS syl_desc
        FROM courses c
        {enrollment_filter}
        LEFT JOIN users u ON u.id = c.owner_id
        LEFT JOIN chapters ch ON ch.course_id = c.id
        LEFT JOIN topics t ON t.chapter_id = ch.id
        LEFT JOIN topic_completions tc ON tc.topic_id = t.id AND tc.user_id = :user_id
        LEFT JOIN materials m ON m.course_id = c.id
        LEFT JOIN course_syllabi sy ON sy.course_id = c.id
        ORDER BY c.id, ch.id, t.`order`
    """)
    rows = db.execute(query, {"user_id": user_id or ""}).fetchall()

    courses_dict = {}
    
    for r in rows:
        cid = r.course_id
        if cid not in courses_dict:
            courses_dict[cid] = {
                "id": cid, "title": r.course_title, "description": r.course_desc,
                "professor_id": r.owner_id,
                "professor_name": r.professor_name or "",
                "student_count": r.student_count or 0,
                "is_open": bool(r.course_is_open),
                "category": r.course_category or "General",
                "image": r.course_image or "",
                "user_role": security.get_course_role(db, user_id, cid) if user_id else None,
                "syllabus": {
                    "id": r.syl_id, "course_id": cid, "course_code": r.course_code or "",
                    "semester": r.semester or "", "instructor_name": r.instructor_name or "",
                    "instructor_email": r.instructor_email or "", "instructor_phone": r.instructor_phone or "",
                    "office_hours": r.office_hours or "", "class_time_location": r.class_time_location or "",
                    "zoom_link": r.zoom_link or "",
                    "description": r.syl_desc or "",
                    "objectives": [], "textbooks": [], "learning_outcomes": []
                } if r.syl_id else None,
                "chapters_dict": {}, "materials_dict": {}
            }
        
        c_obj = courses_dict[cid]
        
        if r.mat_id and r.mat_id not in c_obj["materials_dict"]:
            c_obj["materials_dict"][r.mat_id] = {
                "id": r.mat_id, "name": r.mat_name, "type": r.mat_type, "url": r.mat_url, "course_id": cid
            }
            
        if r.chapter_id:
            chid = r.chapter_id
            if chid not in c_obj["chapters_dict"]:
                c_obj["chapters_dict"][chid] = {
                    "id": chid, "title": r.chapter_title, "summary": r.chapter_summary, 
                    "is_final_quiz_open": bool(r.chapter_is_final_quiz_open), "topics_dict": {}
                }
            ch_obj = c_obj["chapters_dict"][chid]
            
            if r.topic_id:
                tid = r.topic_id
                if tid not in ch_obj["topics_dict"]:
                    ch_obj["topics_dict"][tid] = {
                        "id": tid, "title": r.topic_title, "description": r.topic_desc, 
                        "order": r.topic_order, "completed": (r.completed_by is not None),
                        "is_open": bool(r.topic_is_open)
                    }

    result = []
    for cid, cdata in courses_dict.items():
        if cdata["syllabus"]:
            syl_id = cdata["syllabus"]["id"]
            # Fetch normalized items
            obj_rows = db.execute(text("SELECT text FROM syllabus_objectives WHERE syllabus_id = :sid"), {"sid": syl_id}).fetchall()
            cdata["syllabus"]["objectives"] = [{"text": o[0]} for o in obj_rows]
            
            txt_rows = db.execute(text("SELECT title, author FROM syllabus_textbooks WHERE syllabus_id = :sid"), {"sid": syl_id}).fetchall()
            cdata["syllabus"]["textbooks"] = [{"title": t[0], "author": t[1]} for t in txt_rows]
            
            out_rows = db.execute(text("SELECT text FROM syllabus_outcomes WHERE syllabus_id = :sid"), {"sid": syl_id}).fetchall()
            cdata["syllabus"]["learning_outcomes"] = [{"text": o[0]} for o in out_rows]

        materials = list(cdata.get("materials_dict", {}).values())
        chapters = []
        for chdata in cdata.get("chapters_dict", {}).values():
            topics_list = list(chdata.get("topics_dict", {}).values())
            topics_list.sort(key=lambda x: x["order"])
            chapters.append({
                "id": chdata["id"], "title": chdata["title"], "summary": chdata["summary"],
                "is_final_quiz_open": chdata["is_final_quiz_open"], "topics": topics_list
            })
        
        result.append(schemas.Course.model_validate({
            "id": cdata["id"], "title": cdata["title"], "description": cdata["description"],
            "professor_id": cdata["professor_id"], "professor_name": cdata["professor_name"],
            "student_count": cdata["student_count"], "is_open": cdata["is_open"],
            "user_role": cdata["user_role"],
            "chapters": chapters, "materials": materials,
            "category": cdata["category"], "image": cdata["image"],
            "syllabus": cdata["syllabus"]
        }))
        
    return result

def get_course(db: Session, course_id: str) -> Optional[schemas.Course]:
    res = get_courses(db, user_id="")
    for course in res:
        if course.id == course_id:
            return course
    return None

def create_course(db: Session, data: schemas.CourseCreate, owner_id: str):
    cid = f"c{uuid.uuid4().hex[:8]}"
    db.execute(
        text("INSERT INTO courses (id, title, description, category, image, owner_id, is_open) VALUES (:id, :title, :desc, :cat, :img, :owner, 1)"),
        {"id": cid, "title": data.title, "desc": data.description, "cat": data.category or "General", "img": data.image or "", "owner": owner_id}
    )
    
    # Auto-enroll as owner
    import datetime
    eid = f"e{uuid.uuid4().hex[:8]}"
    db.execute(
        text("INSERT INTO enrollments (id, user_id, course_id, status, role, date) VALUES (:id, :u, :c, 'approved', 'owner', :d)"),
        {"id": eid, "u": owner_id, "c": cid, "d": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    )
    
    db.commit()
    return get_course(db, cid)

def update_course(db: Session, course_id: str, data: schemas.CourseUpdate):
    updates = []
    params = {"id": course_id}
    if data.title is not None:
        updates.append("title = :title"); params["title"] = data.title
    if data.description is not None:
        updates.append("description = :desc"); params["desc"] = data.description
    if data.is_open is not None:
        updates.append("is_open = :is_open"); params["is_open"] = data.is_open
    if data.category is not None:
        updates.append("category = :cat"); params["cat"] = data.category
    if data.image is not None:
        updates.append("image = :img"); params["img"] = data.image
        
    if updates:
        qs = ", ".join(updates)
        db.execute(text(f"UPDATE courses SET {qs} WHERE id = :id"), params)
        db.commit()
        
    return get_course(db, course_id)

def delete_course(db: Session, course_id: str):
    course = db.execute(text("SELECT * FROM courses WHERE id=:id"), {"id": course_id}).fetchone()
    if course:
        db.execute(text("DELETE FROM courses WHERE id=:id"), {"id": course_id})
        db.commit()
    return course

def get_syllabus(db: Session, course_id: str) -> Optional[dict]:
    res = db.execute(text("SELECT * FROM course_syllabi WHERE course_id = :cid"), {"cid": course_id}).fetchone()
    if not res:
        return None
    
    sid = res[0]
    # Fetch normalized
    objs = db.execute(text("SELECT text FROM syllabus_objectives WHERE syllabus_id = :sid"), {"sid": sid}).fetchall()
    txts = db.execute(text("SELECT title, author FROM syllabus_textbooks WHERE syllabus_id = :sid"), {"sid": sid}).fetchall()
    outs = db.execute(text("SELECT text FROM syllabus_outcomes WHERE syllabus_id = :sid"), {"sid": sid}).fetchall()

    return {
        "id": res[0], "course_id": res[1], "course_code": res[2], "semester": res[3],
        "instructor_name": res[4], "instructor_email": res[5], "instructor_phone": res[6],
        "office_hours": res[7], "class_time_location": res[8], "zoom_link": res[9], "description": res[10],
        "objectives": [{"text": o[0]} for o in objs],
        "textbooks": [{"title": t[0], "author": t[1]} for t in txts],
        "learning_outcomes": [{"text": o[0]} for o in outs]
    }

def save_syllabus(db: Session, course_id: str, data: schemas.CourseSyllabusCreate):
    existing = db.execute(text("SELECT id FROM course_syllabi WHERE course_id = :cid"), {"cid": course_id}).fetchone()
    if existing:
        sid = existing[0]
        db.execute(
            text("UPDATE course_syllabi SET course_code=:cc, semester=:sem, instructor_name=:in, instructor_email=:ie, instructor_phone=:ip, office_hours=:oh, class_time_location=:ctl, zoom_link=:zl, description=:desc WHERE id=:sid"),
            {"cc": data.course_code, "sem": data.semester, "in": data.instructor_name, "ie": data.instructor_email, "ip": data.instructor_phone, "oh": data.office_hours, "ctl": data.class_time_location, "zl": data.zoom_link, "desc": data.description, "sid": sid}
        )
        # Delete children to replace
        db.execute(text("DELETE FROM syllabus_objectives WHERE syllabus_id = :sid"), {"sid": sid})
        db.execute(text("DELETE FROM syllabus_textbooks WHERE syllabus_id = :sid"), {"sid": sid})
        db.execute(text("DELETE FROM syllabus_outcomes WHERE syllabus_id = :sid"), {"sid": sid})
    else:
        sid = f"syl{uuid.uuid4().hex[:8]}"
        db.execute(
            text("INSERT INTO course_syllabi (id, course_id, course_code, semester, instructor_name, instructor_email, instructor_phone, office_hours, class_time_location, zoom_link, description) VALUES (:id, :cid, :cc, :sem, :in, :ie, :ip, :oh, :ctl, :zl, :desc)"),
            {"id": sid, "cid": course_id, "cc": data.course_code, "sem": data.semester, "in": data.instructor_name, "ie": data.instructor_email, "ip": data.instructor_phone, "oh": data.office_hours, "ctl": data.class_time_location, "zl": data.zoom_link, "desc": data.description}
        )

    # Insert normalized
    for obj in data.objectives:
        oid = f"obj{uuid.uuid4().hex[:8]}"
        db.execute(text("INSERT INTO syllabus_objectives (id, syllabus_id, text) VALUES (:id, :sid, :t)"), {"id": oid, "sid": sid, "t": obj.text})
    for txt in data.textbooks:
        txid = f"txtb{uuid.uuid4().hex[:8]}"
        db.execute(text("INSERT INTO syllabus_textbooks (id, syllabus_id, title, author) VALUES (:id, :sid, :t, :a)"), {"id": txid, "sid": sid, "t": txt.title, "a": txt.author})
    for out in data.learning_outcomes:
        ouid = f"out{uuid.uuid4().hex[:8]}"
        db.execute(text("INSERT INTO syllabus_outcomes (id, syllabus_id, text) VALUES (:id, :sid, :t)"), {"id": ouid, "sid": sid, "t": out.text})

    db.commit()
    return get_syllabus(db, course_id)
