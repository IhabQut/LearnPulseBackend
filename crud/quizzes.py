from sqlalchemy.orm import Session
from sqlalchemy import text
import schemas
import uuid
import json

def get_quiz_by_topic(db: Session, topic_id: str):
    return db.execute(text("SELECT * FROM quizzes WHERE topic_id=:id AND quiz_type='topic'"), {"id": topic_id}).fetchone()

def get_quiz_by_chapter(db: Session, chapter_id: str):
    return db.execute(text("SELECT * FROM quizzes WHERE chapter_id=:id AND quiz_type='chapter'"), {"id": chapter_id}).fetchone()

def create_quiz(db: Session, data: schemas.QuizCreate):
    qid = f"qz{uuid.uuid4().hex[:8]}"
    db.execute(text("""
        INSERT INTO quizzes (id, title, quiz_type, topic_id, chapter_id)
        VALUES (:id, :title, :type, :topic_id, :chapter_id)
    """), {"id": qid, "title": data.title, "type": data.quiz_type, "topic_id": data.topic_id, "chapter_id": data.chapter_id})
    db.commit()
    return db.execute(text("SELECT * FROM quizzes WHERE id=:id"), {"id": qid}).fetchone()

def add_quiz_question(db: Session, quiz_id: str, data: schemas.QuizQuestionCreate):
    qqid = f"qq{uuid.uuid4().hex[:8]}"
    db.execute(text("""
        INSERT INTO quiz_questions (id, quiz_id, question, explanation)
        VALUES (:id, :quiz_id, :question, :explanation)
    """), {"id": qqid, "quiz_id": quiz_id, "question": data.question, "explanation": data.explanation})
    db.commit()
    
    # Extract options JSON back to database relations
    try:
        opts = json.loads(data.options)
        for idx, opt in enumerate(opts):
            db.execute(text("INSERT INTO quiz_options (id, question_id, text, is_correct) VALUES (:id, :qid, :text, :ic)"),
                       {"id": f"qo{uuid.uuid4().hex[:8]}", "qid": qqid, "text": opt, "ic": (idx == data.correct_option)})
    except Exception as e:
        print("Opts error", e)
    db.commit()
    
    return db.execute(text("SELECT * FROM quiz_questions WHERE id=:id"), {"id": qqid}).fetchone()

def update_quiz_question(db: Session, question_id: str, data: schemas.QuizQuestionUpdate):
    updates = []
    params = {"id": question_id}
    if data.question is not None:
        updates.append("question = :question"); params["question"] = data.question
    if data.explanation is not None:
        updates.append("explanation = :explanation"); params["explanation"] = data.explanation
    if updates:
        db.execute(text(f"UPDATE quiz_questions SET {', '.join(updates)} WHERE id=:id"), params)
        db.commit()
    
    # It might be difficult to update the complex schema dynamically from string, we can drop and insert options
    if data.options is not None and data.correct_option is not None:
        db.execute(text("DELETE FROM quiz_options WHERE question_id=:id"), {"id": question_id})
        try:
            opts = json.loads(data.options)
            for idx, opt in enumerate(opts):
                db.execute(text("INSERT INTO quiz_options (id, question_id, text, is_correct) VALUES (:id, :qid, :text, :ic)"),
                           {"id": f"qo{uuid.uuid4().hex[:8]}", "qid": question_id, "text": opt, "ic": (idx == data.correct_option)})
        except:
            pass
        db.commit()
        
    return db.execute(text("SELECT * FROM quiz_questions WHERE id=:id"), {"id": question_id}).fetchone()

def delete_quiz_question(db: Session, question_id: str):
    res = db.execute(text("SELECT * FROM quiz_questions WHERE id=:id"), {"id": question_id}).fetchone()
    if res:
        db.execute(text("DELETE FROM quiz_questions WHERE id=:id"), {"id": question_id})
        db.commit()
    return res
