import firebase_admin
from firebase_admin import credentials, firestore, auth
from fastapi import HTTPException
import os
from pathlib import Path

# Path to your service‑account JSON file (mounted or env‑configured)
FIREBASE_CRED_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    "D:\Web\Try\si-be4\skillissue-ea816-firebase-adminsdk-fbsvc-c5901a2d97.json"
)

# Initialize Firebase Admin (only if not already initialized)
if not firebase_admin._apps:
    if Path(FIREBASE_CRED_PATH).is_file():
        # Directly pass the path to credentials.Certificate
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to default application credentials
        firebase_admin.initialize_app()

db = firestore.client()

def verify_token(id_token: str):
    try:
        return auth.verify_id_token(id_token)
    except Exception as e:
        # log if needed
        return None

def get_user_details(user_uid: str):
    try:
        print(f"Attempting to fetch user details for UID: {user_uid}")
        user = auth.get_user(user_uid)
        user_details = {
            "email": user.email,
            "name": user.display_name,
            "photo_url": user.photo_url
        }
        print(f"Successfully fetched user details: {user_details}")
        return user_details
    except auth.UserNotFoundError:
        print(f"User not found for UID: {user_uid}")
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        print(f"Error fetching user details for UID {user_uid}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching user: {e}")