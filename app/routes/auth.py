from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.models.firebase import verify_token  # your custom token verifier

router = APIRouter()

class TokenRequest(BaseModel):
    id_token: str


@router.post("/verify")
def verify_user(data: TokenRequest, request: Request):
    try:
        decoded_token = verify_token(data.id_token)
        if not decoded_token:
            raise HTTPException(status_code=403, detail="Invalid or expired token")
        
        uid = decoded_token["uid"]
        email = decoded_token.get("email")

        # Set session
        request.session["user_uid"] = uid
        print(f"Session set for UID: {uid}")  # Debug logging

        return {"message": "Logged in", "uid": uid}
    except Exception as e:
        print("Token verification failed:", str(e))
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/session")
def check_session(request: Request):
    uid = request.session.get("user_uid")
    print(f"Session check - UID: {uid}")  # Debug logging
    if uid:
        return {"logged_in": True, "uid": uid}
    return {"logged_in": False}

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}
