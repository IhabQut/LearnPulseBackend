"""
Role-based access control + JWT authentication for LearnPulse API.
Provides dependency functions for FastAPI routes to validate user identity and permissions.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db

# ─── JWT Configuration ───────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "learnpulse-dev-secret-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# ─── OAuth2 Scheme ───────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token containing the user_id."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """Decode a JWT token and return the user_id, or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None


# ─── Auth Dependencies ───────────────────────────────────────────

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Validate JWT token and return the user row. Raises 401 if invalid."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id}).fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Like get_current_user but returns None instead of raising 401."""
    if not token:
        return None
    user_id = verify_token(token)
    if not user_id:
        return None
    user = db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id}).fetchone()
    return user


# ─── Role & Permission Helpers ────────────────────────────────────

def get_course_role(db: Session, user_id: str, course_id: str):
    """Fetch the specific role of a user in a course."""
    enrollment = db.execute(
        text("SELECT role, status FROM enrollments WHERE user_id=:uid AND course_id=:cid"),
        {"uid": user_id, "cid": course_id}
    ).fetchone()
    if not enrollment or enrollment.status != 'approved':
        return None
    return enrollment.role

def require_course_permission(db: Session, user_id: str, course_id: str, allowed_roles: list):
    """Verify if user has one of the allowed roles in the course."""
    role = get_course_role(db, user_id, course_id)
    if not role:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course.")
    
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Required roles: {allowed_roles}. Your role: {role}")
    return role

def require_professor(user):
    """Global professor check."""
    role = user['role'] if isinstance(user, dict) else user.role
    if role != "professor":
        raise HTTPException(status_code=403, detail="Only professors can perform this action.")
    return user

def require_course_owner(db: Session, user, course_id: str):
    """Strict ownership check for course administration (delete course, manage instructors)."""
    uid = user['id'] if isinstance(user, dict) else user.id
    role = get_course_role(db, uid, course_id)
    if role != 'owner':
        raise HTTPException(status_code=403, detail="Only the course owner can perform this action.")
    return True

def can_manage_role(db: Session, manager_id: str, target_enrollment_id: str, course_id: str):
    """
    Check if manager_id can change the role of target_enrollment_id.
    - Owner can manage anyone except themselves.
    - Instructor can manage students and viewers.
    - Student/Viewer can't manage anyone.
    """
    manager_role = get_course_role(db, manager_id, course_id)
    if not manager_role or manager_role not in ['owner', 'instructor']:
        raise HTTPException(status_code=403, detail="Unauthorized to manage roles.")
    
    target = db.execute(text("SELECT id, user_id, role FROM enrollments WHERE id=:id"), {"id": target_enrollment_id}).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Target enrollment not found.")
    
    if target.user_id == manager_id:
        raise HTTPException(status_code=400, detail="You cannot change your own role.")
        
    if manager_role == 'owner':
        return True # Owner can manage all other roles
        
    if manager_role == 'instructor':
        if target.role in ['owner', 'instructor']:
             raise HTTPException(status_code=403, detail="Instructors cannot manage roles of other instructors or owners.")
        return True
        
    return False
