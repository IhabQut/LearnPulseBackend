import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_permissions():
    print("--- Testing Course Permissions ---")
    
    # 1. Test: Student p4 (as student in c1) tries to update course c1
    # Note: CRUD update_course currently needs user_id.
    # We'll mock the 'u1' (p4) requesting update.
    print("\n1. Testing Student (p4) updating Course (c1)...")
    try:
        response = requests.put(f"{BASE_URL}/courses/c1", 
                              params={"user_id": "u1"}, # p4 is u1 in seed? No, let's check rebuild_db
                              json={"title": "Hacked Title"})
        print(f"Status: {response.status_code}, Detail: {response.json().get('detail')}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Test: Professor p2 (as viewer in c1) tries to update course c1
    print("\n2. Testing Viewer Professor (p2) updating Course (c1)...")
    try:
        response = requests.put(f"{BASE_URL}/courses/c1", 
                              params={"user_id": "p2"}, 
                              json={"title": "Viewer Hack"})
        print(f"Status: {response.status_code}, Detail: {response.json().get('detail')}")
    except Exception as e:
        print(f"Error: {e}")

    # 3. Test: Owner p1 updating course c1
    print("\n3. Testing Owner Professor (p1) updating Course (c1)...")
    try:
        response = requests.put(f"{BASE_URL}/courses/c1", 
                              params={"user_id": "p1"}, 
                              json={"title": "Seed Course 1 (Updated)"})
        print(f"Status: {response.status_code}, Detail: {response.json().get('detail') or 'Success'}")
    except Exception as e:
        print(f"Error: {e}")

    # 4. Test: p2 requesting to be a viewer in c2
    print("\n4. Testing p2 requesting Viewer role in c2...")
    try:
        response = requests.post(f"{BASE_URL}/enrollments/request", 
                               json={"course_id": "c2", "role": "viewer"},
                               params={"user_id": "p2"})
        print(f"Status: {response.status_code}, Message: {response.json().get('message')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_permissions()
