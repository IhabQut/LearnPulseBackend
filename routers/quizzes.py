from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import crud
import schemas
from database import get_db
import json

router = APIRouter(prefix="/api/quizzes", tags=["Quizzes"])

class QuizQuestionOut(BaseModel):
    id: str
    question: str
    options: str  # JSON string
    correct_option: int
    explanation: str
    
class QuizOut(BaseModel):
    id: str
    title: str
    quiz_type: str
    topic_id: Optional[str] = None
    chapter_id: Optional[str] = None
    questions: List[QuizQuestionOut] = []

class QuizSubmission(BaseModel):
    user_id: str = "u1"
    answers: List[int]

def _build_quizout(db, quiz_row):
    questions_res = db.execute(text("SELECT * FROM quiz_questions WHERE quiz_id=:qid"), {"qid": quiz_row.id}).fetchall()
    questions = []
    for q in questions_res:
        opts_res = db.execute(text("SELECT * FROM quiz_options WHERE question_id=:qid"), {"qid": q.id}).fetchall()
        opt_strings = [o.text for o in opts_res]
        correct = next((i for i, o in enumerate(opts_res) if o.is_correct), 0)
        questions.append(QuizQuestionOut(
            id=q.id, question=q.question, options=json.dumps(opt_strings),
            correct_option=correct, explanation=q.explanation
        ))
    return QuizOut(
        id=quiz_row.id, title=quiz_row.title, quiz_type=quiz_row.quiz_type,
        topic_id=quiz_row.topic_id, chapter_id=quiz_row.chapter_id, questions=questions
    )

@router.get("/topic/{topic_id}", response_model=Optional[QuizOut])
def get_topic_quiz(topic_id: str, db: Session = Depends(get_db)):
    qr = db.execute(text("SELECT * FROM quizzes WHERE topic_id=:tid AND quiz_type='topic'"), {"tid": topic_id}).fetchone()
    if not qr: return None
    return _build_quizout(db, qr)

@router.get("/chapter/{chapter_id}", response_model=Optional[QuizOut])
def get_chapter_quiz(chapter_id: str, db: Session = Depends(get_db)):
    qr = db.execute(text("SELECT * FROM quizzes WHERE chapter_id=:cid AND quiz_type='chapter'"), {"cid": chapter_id}).fetchone()
    if not qr: return None
    return _build_quizout(db, qr)

@router.get("/course/{course_id}", response_model=List[QuizOut])
def get_course_quizzes(course_id: str, db: Session = Depends(get_db)):
    quizzes = db.execute(text("""
        SELECT q.* FROM quizzes q
        LEFT JOIN topics t ON t.id = q.topic_id
        LEFT JOIN chapters ch ON ch.id = q.chapter_id OR ch.id = t.chapter_id
        WHERE ch.course_id = :cid
    """), {"cid": course_id}).fetchall()
    return [_build_quizout(db, q) for q in quizzes]

@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(quiz_id: str, db: Session = Depends(get_db)):
    qr = db.execute(text("SELECT * FROM quizzes WHERE id=:id"), {"id": quiz_id}).fetchone()
    if not qr: raise HTTPException(404)
    return _build_quizout(db, qr)

@router.post("/{quiz_id}/submit", response_model=schemas.QuizAttemptOut)
def submit_quiz(quiz_id: str, submission: QuizSubmission, db: Session = Depends(get_db)):
    quiz_row = db.execute(text("SELECT * FROM quizzes WHERE id=:id"), {"id": quiz_id}).fetchone()
    if not quiz_row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    qz = _build_quizout(db, quiz_row)
    score = 0
    for i, q in enumerate(qz.questions):
        if i < len(submission.answers) and submission.answers[i] == q.correct_option:
            score += 1
            
    prior = db.execute(text("SELECT id FROM quiz_attempts WHERE user_id=:u AND quiz_id=:q"), 
                       {"u": submission.user_id, "q": quiz_id}).fetchone()
    is_first = prior is None
    import uuid
    aid = str(uuid.uuid4())
    db.execute(text("INSERT INTO quiz_attempts (id, user_id, quiz_id, score, total, date, is_first_attempt) VALUES (:id, :u, :q, :s, :t, 'Just now', :f)"),
               {"id": aid, "u": submission.user_id, "q": quiz_id, "s": score, "t": len(qz.questions), "f": is_first})
    db.commit()
    pts = 0
    if is_first:
        pts = score * 5
        crud.award_points(db, submission.user_id, pts)
    return schemas.QuizAttemptOut(
        id=aid, user_id=submission.user_id, quiz_id=quiz_id, score=score, total=len(qz.questions),
        date="Just now", is_first_attempt=is_first, points_awarded=pts
    )

@router.get("/course/{course_id}/attempts", response_model=List[schemas.StudentQuizAttempt])
def get_course_quiz_attempts(course_id: str, db: Session = Depends(get_db)):
    attempts = db.execute(text("""
        SELECT qa.*, q.title as quiz_title, u.name as user_name
        FROM quiz_attempts qa
        JOIN quizzes q ON q.id = qa.quiz_id
        JOIN users u ON u.id = qa.user_id
        LEFT JOIN topics t ON t.id = q.topic_id
        LEFT JOIN chapters ch ON ch.id = q.chapter_id OR ch.id = t.chapter_id
        WHERE ch.course_id = :cid
    """), {"cid": course_id}).fetchall()
    return [schemas.StudentQuizAttempt.model_validate(dict(a._mapping)) for a in attempts]

@router.get("/student/{student_id}/attempts", response_model=List[schemas.StudentQuizAttempt])
def get_student_quiz_attempts(student_id: str, db: Session = Depends(get_db)):
    attempts = db.execute(text("""
        SELECT qa.*, q.title as quiz_title, '' as user_name
        FROM quiz_attempts qa
        JOIN quizzes q ON q.id = qa.quiz_id
        WHERE qa.user_id = :u
    """), {"u": student_id}).fetchall()
    return [schemas.StudentQuizAttempt.model_validate(dict(a._mapping)) for a in attempts]

@router.post("/topic/{topic_id}", response_model=QuizOut)
def create_topic_quiz(topic_id: str, data: schemas.QuizCreate, db: Session = Depends(get_db)):
    quiz = crud.get_quiz_by_topic(db, topic_id)
    if not quiz: quiz = crud.create_quiz(db, data)
    return _build_quizout(db, quiz)

@router.post("/chapter/{chapter_id}", response_model=QuizOut)
def create_chapter_quiz(chapter_id: str, data: schemas.QuizCreate, db: Session = Depends(get_db)):
    quiz = crud.get_quiz_by_chapter(db, chapter_id)
    if not quiz: quiz = crud.create_quiz(db, data)
    return _build_quizout(db, quiz)

@router.post("/{quiz_id}/questions", response_model=QuizQuestionOut)
def add_question(quiz_id: str, data: schemas.QuizQuestionCreate, db: Session = Depends(get_db)):
    crud.add_quiz_question(db, quiz_id, data)
    qr = db.execute(text("SELECT * FROM quizzes WHERE id=:id"), {"id": quiz_id}).fetchone()
    qz = _build_quizout(db, qr)
    return qz.questions[-1]

@router.put("/questions/{question_id}", response_model=QuizQuestionOut)
def update_question(question_id: str, data: schemas.QuizQuestionUpdate, db: Session = Depends(get_db)):
    crud.update_quiz_question(db, question_id, data)
    qz = db.execute(text("SELECT quiz_id FROM quiz_questions WHERE id=:id"), {"id": question_id}).fetchone()
    qr = db.execute(text("SELECT * FROM quizzes WHERE id=:id"), {"id": qz.quiz_id}).fetchone()
    qzout = _build_quizout(db, qr)
    return next((q for q in qzout.questions if q.id == question_id), None)

@router.delete("/questions/{question_id}")
def delete_question(question_id: str, db: Session = Depends(get_db)):
    crud.delete_quiz_question(db, question_id)
    return {"status": "success"}
