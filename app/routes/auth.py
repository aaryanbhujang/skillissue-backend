# app/routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# Initialize Firebase Admin once (move this to a separate init module in prod)
cred = credentials.Certificate("/etc/secrets/skillissue-ea816-firebase-adminsdk-fbsvc-8cc10a29d9.json")
firebase_admin.initialize_app(cred)

router = APIRouter()

class TokenRequest(BaseModel):
    id_token: str

@router.post("/verify")
def verify_user(data: TokenRequest):
    try:
        decoded_token = firebase_auth.verify_id_token(data.id_token)
        print(decoded_token)
        uid = decoded_token["uid"]
        email = decoded_token.get("email")
        return {"uid": uid, "email": email}
    except Exception as e:
        print("Token verification failed:", str(e))
        raise HTTPException(status_code=401, detail="Invalid token")
