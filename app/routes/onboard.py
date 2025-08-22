from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from app.models.firebase import get_user_details 
from typing import List, Dict, Optional
from google.cloud import firestore
from app.models.firebase import db
router = APIRouter()


class ProjectSchema(BaseModel):
    title: str
    description: str
    tech_stack: List[str]
    requirements: List[str]

class OnboardingRequest(BaseModel):
    name: str
    email: str
    photo_url: Optional[str] = Field(
        default=None,
        description="URL of user's avatar; null if not provided"
    )
    skills: Optional[List[str]] = Field(
        default=None,
        description="List of skill IDs; null if none"
    )
    preferences: Optional[List[str]] = Field(
        default=None,
        description="List of preference IDs; null if none"
    )
    projects: Optional[Dict[str, ProjectSchema]] = Field(
        default=None,
        description="Map project_id → project details; null if none"
    )

@router.post("/register")
def onboardUser(request: Request, data: OnboardingRequest):
    print("Onboarding user with data:", data)
    uid = request.session.get("user_uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Not verified, innit")
    else:
        userdetails = get_user_details(uid)
        print(userdetails)
        user_ref = db.collection("users").document(uid)

    # Build the payload, omitting any None fields
    payload = {
        "name": data.name,
        "email": data.email,
        "onboarded": True,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    if data.photo_url is not None:
        payload["photo_url"] = data.photo_url
    if data.skills is not None:
        payload["skills"] = data.skills
    if data.preferences is not None:
        payload["preferences"] = data.preferences
    if data.projects is not None:
        # embed the dict of ProjectSchema as raw dicts
        payload["projects"] = {pid: proj.dict() for pid, proj in data.projects.items()}

    # Merge into user document
    user_ref.set(payload, merge=True)

    # Optionally handle user_skills and user_preferences only if provided
    batch = db.batch()
    if data.skills:
        for skill_id in data.skills:
            us_ref = db.collection("user_skills").document()
            batch.set(us_ref, {
                "uid": uid,  # Store the UID string instead of document reference
                "skill_id": skill_id  # Store the skill ID string instead of document reference
            })
    if data.preferences:
        for pref_id in data.preferences:
            up_ref = db.collection("user_preferences").document()
            batch.set(up_ref, {
                "uid": uid,  # Store the UID string instead of document reference
                "pref_id": pref_id  # Store the preference ID string instead of document reference
            })
    if data.skills or data.preferences:
        batch.commit()

    return {"message": "Onboarding complete", "uid": uid}