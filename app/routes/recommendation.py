from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from google.cloud import firestore
from app.models.firebase import db, get_user_details

router = APIRouter()

@router.get("/recommendations")
def get_recommendations(request: Request):
    uid = request.session.get("user_uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Not verified, innit")

    # Fetch user details
    try:
        userdetails = get_user_details(uid)
        print("User details from Firebase:", userdetails)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")

    # TODO: Implement recommendation logic here

    return {"message": "Recommendations fetched successfully", "data": []}
