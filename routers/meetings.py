from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

import crud
import schemas
import models
from database import get_db

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])

@router.post("", response_model=schemas.MeetingRequestOut)
def create_meeting(data: schemas.MeetingRequestCreate, user_id: str = None, db: Session = Depends(get_db)):
    # In a real app, user_id would come from a JWT token. 
    # For this mock, we'll allow it as a param or default to u1.
    uid = user_id or "u1"
    meeting = crud.create_meeting_request(db, uid, data)
    
    user = crud.get_user(db, meeting.user_id)
    professor = crud.get_user(db, meeting.professor_id)
    
    # Notify professor
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=meeting.professor_id,
        title="New Meeting Request",
        message=f"{user.name if user else 'A student'} has requested a meeting on {meeting.slot}.",
        type="info",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return schemas.MeetingRequestOut(
        **meeting.__dict__,
        user_name=user.name if user else "Unknown",
        professor_name=professor.name if professor else "Unknown"
    )

@router.get("", response_model=List[schemas.MeetingRequestOut])
def get_meetings(user_id: str = None, db: Session = Depends(get_db)):
    uid = user_id or "u1"
    meetings = crud.get_meeting_requests(db, uid)
    result = []
    for m in meetings:
        user = crud.get_user(db, m.user_id)
        professor = crud.get_user(db, m.professor_id)
        result.append(schemas.MeetingRequestOut(
            **m.__dict__,
            user_name=user.name if user else "Unknown",
            professor_name=professor.name if professor else "Unknown"
        ))
    return result

@router.put("/{meeting_id}", response_model=schemas.MeetingRequestOut)
def update_meeting_status(meeting_id: str, status: str, db: Session = Depends(get_db)):
    meeting = crud.update_meeting_status(db, meeting_id, status)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    user = crud.get_user(db, meeting.user_id)
    professor = crud.get_user(db, meeting.professor_id)
    
    # Notify student
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=meeting.user_id,
        title=f"Meeting {status.capitalize()}",
        message=f"Professor {professor.name if professor else 'Unknown'} has {status} your meeting request for {meeting.slot}.",
        type="success" if status == "approved" else "warning",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return schemas.MeetingRequestOut(
        **meeting.__dict__,
        user_name=user.name if user else "Unknown",
        professor_name=professor.name if professor else "Unknown"
    )
