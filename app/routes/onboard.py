from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field 
from typing import List, Dict, Optional
from google.cloud import firestore
from app.models.firebase import db
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from sentence_transformers import SentenceTransformer
import numpy as np

router = APIRouter()

# Initialize embedder once
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Connect to Qdrant
qdrant_client = QdrantClient(
    url="https://220a92ad-60e4-46d4-ad37-55ef2981f953.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.Vf-nEfun8kIzTeP9-MHwmJk3jVy2oyways2cyUXAJm8",
)

# Ensure collections exist
def ensure_collections():
    collections = [c.name for c in qdrant_client.get_collections().collections]
    if "users" not in collections:
        qdrant_client.create_collection(
            collection_name="users",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)  # MiniLM = 384
        )
    if "projects" not in collections:
        qdrant_client.create_collection(
            collection_name="projects",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

ensure_collections()


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


# Embedding utility
def embed(values: list[str], weights: list[float] | None = None) -> list[float]:
    if not values:
        return []

    vectors = embedder.encode(values)
    if weights:
        weighted_vecs = [vec * w for vec, w in zip(vectors, weights)]
        final_vector = np.mean(weighted_vecs, axis=0)
    else:
        final_vector = vectors.mean(axis=0)
    return final_vector.tolist()


@router.post("/register")
def onboardUser(request: Request, data: OnboardingRequest):
    print("Onboarding user with data:", data)
    uid = request.session.get("user_uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Not verified, innit")

    # Firestore: Create/update user document
    user_ref = db.collection("users").document(uid)
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

    user_ref.set(payload, merge=True)

    # Firestore: user_skills & user_preferences
    batch = db.batch()
    if data.skills:
        for skill_id in data.skills:
            us_ref = db.collection("user_skills").document()
            batch.set(us_ref, {"uid": uid, "skill_id": skill_id})
    if data.preferences:
        for pref_id in data.preferences:
            up_ref = db.collection("user_preferences").document()
            batch.set(up_ref, {"uid": uid, "pref_id": pref_id})
    if data.skills or data.preferences:
        batch.commit()

    # Only after Firestore writes succeed → push to Qdrant

    # --- USER VECTOR ---
    user_values, weights = [], []
    if data.skills:
        user_values.extend(data.skills)
        weights.extend([0.6] * len(data.skills))
    if data.preferences:
        user_values.extend(data.preferences)
        weights.extend([0.3] * len(data.preferences))
    if data.projects:
        titles = [proj.title for proj in data.projects.values()]
        user_values.extend(titles)
        weights.extend([0.1] * len(titles))

    if user_values:
        user_vector = embed(user_values, weights)
        qdrant_client.upsert(
            collection_name="users",
            points=[{
                "id": uid,   # Use UID from Firestore
                "vector": user_vector,
                "payload": {
                    "username": data.name,
                    "email": data.email,
                    "skills": data.skills,
                    "preferences": data.preferences,
                    "projects": list(data.projects.keys()) if data.projects else []
                }
            }]
        )

    # --- PROJECT VECTORS ---
    if data.projects:
        for pid, proj in data.projects.items():
            proj_values, proj_weights = [], []
            proj_values.extend(proj.tech_stack)
            proj_weights.extend([0.7] * len(proj.tech_stack))
            proj_values.extend(proj.requirements)
            proj_weights.extend([0.3] * len(proj.requirements))

            proj_vector = embed(proj_values, proj_weights)
            qdrant_client.upsert(
                collection_name="projects",
                points=[{
                    "id": pid,   #Use project ID, not title
                    "vector": proj_vector,
                    "payload": {
                        "title": proj.title,
                        "description": proj.description,
                        "tech_stack": proj.tech_stack,
                        "requirements": proj.requirements
                    }
                }]
            )

    return {"message": "Onboarding complete", "uid": uid}