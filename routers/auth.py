from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import logging

import crud
import schemas
from database import get_db
from security import hash_password, verify_password, create_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=schemas.TokenResponse)
def register(request: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email and password."""
    # Check if email already exists
    existing = db.execute(
        text("SELECT id FROM users WHERE email=:email"),
        {"email": request.email}
    ).fetchone()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Create user
    user_id = f"{'u' if request.role == 'student' else 'p'}_{uuid.uuid4().hex[:8]}"
    hashed_pw = hash_password(request.password)

    db.execute(text(
        "INSERT INTO users (id, name, role, email, password_hash, phone_number, bio) "
        "VALUES (:id, :name, :role, :email, :pw, '', '')"
    ), {
        "id": user_id,
        "name": request.name,
        "role": request.role,
        "email": request.email,
        "pw": hashed_pw,
    })

    # Create specialized profile
    if request.role == "professor":
        db.execute(text(
            "INSERT INTO professors (id, department, expertise, academic_rank) VALUES (:id, '', '', '')"
        ), {"id": user_id})
    else:
        db.execute(text(
            "INSERT INTO students (id, major, level, gpa) VALUES (:id, '', 'Undergraduate', 0.0)"
        ), {"id": user_id})

    db.commit()

    # Generate token
    token = create_access_token(user_id)
    user_data = crud.get_user(db, user_id)

    logger.info(f"New user registered: {request.email} as {request.role}")
    return {"access_token": token, "token_type": "bearer", "user": user_data}


@router.post("/login", response_model=schemas.TokenResponse)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password, returns JWT token."""
    user = db.execute(
        text("SELECT * FROM users WHERE email=:email"),
        {"email": request.email}
    ).fetchone()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Generate token
    token = create_access_token(user.id)
    user_data = crud.get_user(db, user.id)

    logger.info(f"User logged in: {request.email}")
    return {"access_token": token, "token_type": "bearer", "user": user_data}


@router.get("/me", response_model=schemas.User)
def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the currently authenticated user's full profile."""
    uid = current_user.id if hasattr(current_user, 'id') else current_user['id']
    user_data = crud.get_user(db, uid)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found.")
    return user_data
