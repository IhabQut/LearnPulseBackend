from sqlalchemy.orm import Session
from sqlalchemy import text
import schemas
import uuid

def create_material(db: Session, course_id: str, data: schemas.MaterialCreate):
    mid = f"mat{uuid.uuid4().hex[:8]}"
    db.execute(text("INSERT INTO materials (id, name, type, url, course_id) VALUES (:id, :n, :t, :u, :c)"),
               {"id": mid, "n": data.name, "t": data.type, "u": data.url, "c": course_id})
    db.commit()
    return db.execute(text("SELECT * FROM materials WHERE id=:id"), {"id": mid}).fetchone()

def delete_material(db: Session, material_id: str):
    res = db.execute(text("SELECT * FROM materials WHERE id=:id"), {"id": material_id}).fetchone()
    if res:
        db.execute(text("DELETE FROM materials WHERE id=:id"), {"id": material_id})
        db.commit()
    return res
