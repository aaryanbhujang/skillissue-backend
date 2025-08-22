from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from google.cloud import firestore
from app.models.firebase import db, get_user_details

router = APIRouter()


# ---- Pydantic Schemas ----
class ProjectSchema(BaseModel):
    title: str
    description: str
    tech_stack: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)


class OnboardingRequest(BaseModel):
    name: str
    email: str
    photo_url: Optional[str] = Field(
        default=None,
        description="URL of user's avatar; null if not provided"
    )
    skills: Optional[List[str]] = Field(
        default=None,
        description="List of skill names; null if none"
    )
    preferences: Optional[List[str]] = Field(
        default=None,
        description="List of preference names; null if none"
    )
    projects: Optional[Dict[str, ProjectSchema]] = Field(
        default=None,
        description="Map project_id → project details; null if none"
    )


# ---- Endpoint ----
@router.post("/register")
def onboard_user(request: Request, data: OnboardingRequest):
    uid = request.session.get("user_uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Not verified, innit")

    # Make sure user exists in Firebase Auth
    # try:
    #     userdetails = get_user_details(uid)
    #     print("User details from Firebase:", userdetails)
    # except Exception as e:
    #     raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")

    user_ref = db.collection("users").document(uid)

    # Build user payload
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
        payload["projects"] = {pid: proj.dict() for pid, proj in data.projects.items()}

    # Save user doc
    user_ref.set(payload, merge=True)

    # ---- Handle global projects ----
    if data.projects:
        batch = db.batch()
        for pid, proj in data.projects.items():
            proj_ref = db.collection("projects").document(pid)
            batch.set(proj_ref, {
                "created_by": uid,
                "title": proj.title,
                "desc": proj.description,
                "tech_stack": proj.tech_stack,
                "requirements": proj.requirements,
            }, merge=True)
        batch.commit()

    # ---- Handle global skills ----
    if data.skills:
        batch = db.batch()
        for skill in set(data.skills):
            skill_id = skill.strip().lower()
            skill_ref = db.collection("skills").document(skill_id)
            batch.set(skill_ref, {"name": skill}, merge=True)
        batch.commit()

    # ---- Handle global preferences ----
    if data.preferences:
        batch = db.batch()
        for pref in set(data.preferences):
            pref_id = pref.strip().lower()
            pref_ref = db.collection("preferences").document(pref_id)
            batch.set(pref_ref, {"name": pref}, merge=True)
        batch.commit()

    return {"message": "Onboarding complete", "uid": uid}
