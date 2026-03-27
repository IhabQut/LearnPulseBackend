from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import crud
import schemas
from database import get_db

router = APIRouter(prefix="/api", tags=["Materials"])

@router.post("/materials", response_model=schemas.Material)
def create_material(course_id: str, data: schemas.MaterialCreate, db: Session = Depends(get_db)):
    material = crud.create_material(db, course_id, data)
    return schemas.Material.model_validate(material)

@router.delete("/materials/{material_id}")
def delete_material(material_id: str, db: Session = Depends(get_db)):
    material = crud.delete_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "Material deleted successfully"}
