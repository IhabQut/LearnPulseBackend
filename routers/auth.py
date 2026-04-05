from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

import crud
import schemas
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["Auth"])

from typing import Optional

class LoginRequest(BaseModel):
    role: str
    user_id: Optional[str] = None

@router.post("/login", response_model=schemas.User)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user_id = request.user_id if request.user_id else ('u1' if request.role == 'student' else 'p1')
    user = crud.get_user(db, user_id=user_id)
    if not user:
        user_data = schemas.UserBase(
            id=user_id,
            name="Sara" if request.role == "student" else "Prof. Smith",
            role=request.role,
            email="",
            phone_number="",
            bio=""
        )
        user = crud.create_user(db, user_data)
    return user
