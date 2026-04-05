from sqlalchemy.orm import Session
from database import engine, get_db
import crud
import security
import schemas
import models

def test_internal_permissions():
    print("--- Internal Permissions Verification ---")
    db = Session(bind=engine)
    
    try:
        # 1. Test: p1 is Owner of c1. Should have permission.
        print("\n1. Testing Owner (p1) permission for Course (c1)...")
        user_p1 = crud.get_user(db, "p1")
        try:
            security.require_course_owner(db, user_p1, "c1")
            print("p1 is verified as Owner of c1: Success")
        except Exception as e:
            print(f"p1 Owner check failed: {e}")

        # 2. Test: p2 is Viewer of c1 (seeded). Should NOT have owner permission.
        print("\n2. Testing Viewer (p2) for Owner permission in Course (c1)...")
        user_p2 = crud.get_user(db, "p2")
        try:
            security.require_course_owner(db, user_p2, "c1")
            print("p2 was incorrectly allowed as Owner")
        except Exception as e:
            print(f"p2 Viewer rejected for Owner action: Success (Expected 403: {e})")

        # 3. Test: p2 (Viewer) requesting 'instructor' permission check.
        print("\n3. Testing Viewer (p2) for Instructor permission in Course (c1)...")
        try:
            security.require_course_permission(db, "p2", "c1", allowed_roles=["owner", "instructor"])
            print("p2 was incorrectly allowed as Instructor")
        except Exception as e:
            print(f"p2 Viewer rejected for Instructor action: Success (Expected 403: {e})")

        # 4. Test: Promote s1 (u1) to Instructor in c2
        print("\n4. Testing Promotion of Student (u1) to Instructor in Course (c2)...")
        crud.enroll_student_directly(db, "u1", "c2", role="instructor")
        db.commit()
        try:
            security.require_course_permission(db, "u1", "c2", allowed_roles=["instructor"])
            print("u1 (Student) is now an Instructor in c2: Success")
        except Exception as e:
            print(f"u1 Instructor promotion check failed: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    test_internal_permissions()
