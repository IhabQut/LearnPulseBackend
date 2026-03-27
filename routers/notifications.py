from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import crud
import schemas
from database import get_db

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("/", response_model=List[schemas.Notification])
def read_notifications(user_id: str, db: Session = Depends(get_db)):
    return crud.get_notifications(db, user_id=user_id)

@router.put("/{notification_id}/read", response_model=schemas.Notification)
def mark_read(notification_id: str, db: Session = Depends(get_db)):
    notification = crud.mark_notification_read(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification

@router.delete("/{notification_id}")
def delete_notification(notification_id: str, db: Session = Depends(get_db)):
    notification = crud.delete_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}
