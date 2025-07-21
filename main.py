from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.routes import auth

app = FastAPI(title="SkillIssue Backend API", version="1.0.0")

origins = [
    "http://localhost:5173",  # React app
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Can be ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],              # Allow all HTTP methods
    allow_headers=["*"],              # Allow all headers
)
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/")
def home():
    return {"message": "I hope this works "}
