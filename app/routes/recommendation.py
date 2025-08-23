from fastapi import APIRouter, HTTPException, Request
from app.models.firebase import db
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

router = APIRouter()

# Initialize Sentence Transformer once
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Connect Qdrant
qdrant_client = QdrantClient(
    url="https://220a92ad-60e4-46d4-ad37-55ef2981f953.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.Vf-nEfun8kIzTeP9-MHwmJk3jVy2oyways2cyUXAJm8",
)


@router.get("/recommendations")
def get_recommendations(request: Request):
    uid = request.session.get("user_uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Not verified, innit")

    # Fetch user details from Firestore
    try:
        user_doc = db.collection("users").document(uid).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User profile not found")
        user_data = user_doc.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user profile: {str(e)}")

    # Collect values for embedding
    values = []
    if "skills" in user_data and user_data["skills"]:
        values.extend(user_data["skills"])
    if "preferences" in user_data and user_data["preferences"]:
        values.extend(user_data["preferences"])

    if not values:
        return {"message": "No skills or preferences found", "data": []}

    # Generate query vector
    query_vector = embedder.encode(" ".join(values)).tolist()

    # Search in Qdrant users collection
    search_results = qdrant_client.search(
        collection_name="users",
        query_vector=query_vector,
        limit=10
    )

    matches = []
    for result in search_results:
        if result.score >= 0.4 and str(result.id) != uid:
            # Fetch actual user from Firestore
            user_ref = db.collection("users").document(str(result.id))
            user_doc = user_ref.get()
            if user_doc.exists:
                user_info = user_doc.to_dict()
                matches.append({
                    "id": result.id,
                    "score": result.score,
                    "user": user_info  # Actual Firestore user data
                })

    return {"message": "Recommendations fetched successfully", "data": matches}