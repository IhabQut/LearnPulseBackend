from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
import schemas
import crud
from database import get_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.post("/chapter/{chapter_id}/summary")
def generate_chapter_summary(chapter_id: str, db: Session = Depends(get_db)):
    chapter = db.execute(text("SELECT * FROM chapters WHERE id=:id"), {"id": chapter_id}).fetchone()
    if not chapter: return {"summary": "Chapter not found."}
    
    topics = db.execute(text("SELECT title FROM topics WHERE chapter_id=:id"), {"id": chapter_id}).fetchall()
    if not topics: return {"summary": "No topics found in this chapter to summarize."}
    
    topic_titles = [t.title for t in topics]
    summary_start = f"In this chapter on {chapter.title}, we explore {len(topic_titles)} key concepts: "
    if len(topic_titles) > 1:
        summary_body = ", ".join(topic_titles[:-1]) + f", and {topic_titles[-1]}"
    else:
        summary_body = topic_titles[0]
    summary_end = ". Students will gain a foundational understanding of these areas and their practical applications."
    return {"summary": f"{summary_start}{summary_body}{summary_end}"}

@router.get("/course/{course_id}", response_model=schemas.AIReport)
def get_course_analytics(course_id: str, db: Session = Depends(get_db)):
    c = db.execute(text("SELECT title FROM courses WHERE id=:id"), {"id": course_id}).fetchone()
    if not c: return schemas.AIReport(course_title="Unknown", total_students=0, insight="Course not found.")

    enrolled = db.execute(text("SELECT user_id FROM enrollments WHERE course_id=:cid AND status='approved'"), {"cid": course_id}).fetchall()
    enrolled_ids = [e.user_id for e in enrolled]
    
    if not enrolled_ids:
        all_s = db.execute(text("SELECT id FROM users WHERE role='student'")).fetchall()
        enrolled_ids = [s.id for s in all_s]

    topics = db.execute(text("""
        SELECT t.id, t.title, ch.title as ch_title
        FROM topics t
        JOIN chapters ch ON ch.id = t.chapter_id
        WHERE ch.course_id = :cid
    """), {"cid": course_id}).fetchall()

    struggling = []
    for t in topics:
        q = db.execute(text("SELECT id FROM quizzes WHERE topic_id=:tid"), {"tid": t.id}).fetchone()
        if not q: continue
        res = db.execute(text("SELECT SUM(score) as sum_s, SUM(total) as sum_t FROM quiz_attempts WHERE quiz_id=:qid AND is_first_attempt=1"), {"qid": q.id}).fetchone()
        if res and res.sum_t and res.sum_t > 0:
            fail_rate = round((1 - (res.sum_s / res.sum_t)) * 100, 1)
            if fail_rate > 20:
                struggling.append(schemas.StrugglingTopic(
                    topic_title=t.title, chapter_title=t.ch_title, fail_rate=fail_rate,
                    common_mistake=f"{fail_rate}% of students answered incorrectly."
                ))
    struggling.sort(key=lambda x: x.fail_rate, reverse=True)

    low_participation = []
    high_performers = []
    for uid in enrolled_ids:
        u = db.execute(text("SELECT name FROM users WHERE id=:uid"), {"uid": uid}).fetchone()
        if not u: continue
        
        tc = db.execute(text("""
            SELECT COUNT(*) as c FROM topic_completions tc
            JOIN topics t ON t.id = tc.topic_id
            JOIN chapters ch ON ch.id = t.chapter_id
            WHERE tc.user_id = :uid AND ch.course_id = :cid
        """), {"uid": uid, "cid": course_id}).fetchone().c
        
        qc = db.execute(text("""
            SELECT COUNT(*) as c FROM quiz_attempts qa
            JOIN quizzes q ON q.id = qa.quiz_id
            LEFT JOIN topics t ON t.id = q.topic_id
            LEFT JOIN chapters ch ON ch.id = q.chapter_id OR ch.id = t.chapter_id
            WHERE qa.user_id = :uid AND ch.course_id = :cid
        """), {"uid": uid, "cid": course_id}).fetchone().c
        
        entry = schemas.StudentParticipation(student_id=uid, student_name=u.name, topics_completed=tc, quizzes_taken=qc)
        if tc == 0 and qc == 0: low_participation.append(entry)
        elif tc >= len(topics) * 0.7: high_performers.append(entry)

    insight_parts = []
    if struggling: insight_parts.append(f"Students are struggling most with '{struggling[0].topic_title}' ({struggling[0].fail_rate}% fail rate).")
    if low_participation: insight_parts.append(f"Students not participating: {', '.join(s.student_name for s in low_participation[:3])}.")
    if high_performers: insight_parts.append(f"{len(high_performers)} students are performing above average.")
    
    return schemas.AIReport(
        course_title=c.title, total_students=len(enrolled_ids),
        struggling_topics=struggling, low_participation=low_participation,
        high_performers=high_performers,
        insight=" ".join(insight_parts) if insight_parts else "Not enough data to generate insights yet."
    )

@router.get("/student/{student_id}", response_model=schemas.StudentAnalyticsOut)
def get_student_analytics(student_id: str, db: Session = Depends(get_db)):
    qh = db.execute(text("""
        SELECT qa.*, q.title as quiz_title, '' as user_name
        FROM quiz_attempts qa
        JOIN quizzes q ON q.id = qa.quiz_id
        WHERE qa.user_id = :uid
    """), {"uid": student_id}).fetchall()
    quiz_history = [schemas.StudentQuizAttempt.model_validate(dict(a._mapping)) for a in qh]
    
    rec = crud.get_next_recommended_topic(db, student_id)
    
    res = db.execute(text("""
        SELECT 
            (SELECT COUNT(*) FROM topics t JOIN chapters ch ON ch.id = t.chapter_id JOIN enrollments e ON e.course_id = ch.course_id WHERE e.user_id = :uid AND e.status='approved') as total_t,
            (SELECT COUNT(*) FROM topic_completions tc JOIN topics t ON t.id = tc.topic_id JOIN chapters ch ON ch.id = t.chapter_id JOIN enrollments e ON e.course_id = ch.course_id WHERE e.user_id = :uid AND tc.user_id = :uid AND e.status='approved') as comp_t
    """), {"uid": student_id}).fetchone()
    
    prog = (res.comp_t / res.total_t * 100) if res.total_t > 0 else 0
    return schemas.StudentAnalyticsOut(quiz_attempts=quiz_history, recommended_topics=rec, overall_progress=round(prog, 1))
