from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import crud
import schemas
from database import get_db

router = APIRouter(prefix="/api", tags=["Course Builder"])


# ─── Textbook ────────────────────────────────────────────────────

@router.post("/courses/{course_id}/textbook")
def save_textbook(course_id: str, data: schemas.CourseTextbookCreate, db: Session = Depends(get_db)):
    crud.save_course_textbook(db, course_id, data.model_dump())
    return {"message": "Textbook saved"}


# ─── Chapters (bulk) ─────────────────────────────────────────────

@router.post("/courses/{course_id}/chapters/bulk")
def bulk_save_chapters(course_id: str, data: schemas.BulkSaveChaptersRequest, db: Session = Depends(get_db)):
    chapters = [ch.model_dump() for ch in data.chapters]
    crud.bulk_save_chapters(db, course_id, chapters)
    return {"message": f"Saved {len(chapters)} chapters"}


# ─── Grading ─────────────────────────────────────────────────────

@router.post("/courses/{course_id}/grading")
def save_grading(course_id: str, data: schemas.SaveGradingRequest, db: Session = Depends(get_db)):
    components = [c.model_dump() for c in data.components]
    crud.save_grading_components(db, course_id, components)
    return {"message": "Grading saved"}


@router.get("/courses/{course_id}/grading", response_model=List[schemas.GradingComponentOut])
def get_grading(course_id: str, db: Session = Depends(get_db)):
    return crud.get_grading_components(db, course_id)


# ─── Semester Plan ────────────────────────────────────────────────

@router.post("/courses/{course_id}/semester-plan")
def save_semester_plan(course_id: str, data: schemas.SaveSemesterPlanRequest, db: Session = Depends(get_db)):
    weeks = [w.model_dump() for w in data.weeks]
    crud.save_semester_plan(db, course_id, weeks)
    return {"message": "Semester plan saved"}


@router.get("/courses/{course_id}/semester-plan", response_model=List[schemas.SemesterWeekOut])
def get_semester_plan(course_id: str, db: Session = Depends(get_db)):
    return crud.get_semester_plan(db, course_id)
