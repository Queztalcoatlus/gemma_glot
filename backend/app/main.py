from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth import current_user, hash_password, issue_token, verify_password
from backend.app.db import get_db, init_db
from backend.app.inference import InferenceError, analyze_audio, analyze_text
from backend.app.models import User
from backend.app.schemas import AuthRequest, AuthResponse, SaveVocabularyRequest, UserResponse
from backend.app.storage import get_analysis, list_history, list_vocabulary, save_analysis, save_vocabulary_selection


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
MAX_AUDIO_BYTES = 16 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/webm",
}


app = FastAPI(title="GemmaGlot", version="0.1.0")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
async def startup() -> None:
    init_db()


class TextAnalysisRequest(BaseModel):
    language: str = "Spanish"
    text: str = Field(min_length=1, max_length=12000)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "backend": "google-or-vllm"}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    username = request.username.strip()
    user = User(username=username, password_hash=hash_password(request.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username is already taken.") from exc
    db.refresh(user)
    return AuthResponse(token=issue_token(db, user), username=user.username)


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.username == request.username.strip()))
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return AuthResponse(token=issue_token(db, user), username=user.username)


@app.get("/api/auth/me", response_model=UserResponse)
async def me(user: User = Depends(current_user)) -> UserResponse:
    return UserResponse(username=user.username)


@app.post("/api/analyze/text")
async def analyze_text_endpoint(
    request: TextAnalysisRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Enter Spanish text to analyze.")

    try:
        analysis = await analyze_text(text, request.language)
    except InferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    save_analysis(db, user, analysis)
    return analysis


@app.post("/api/analyze/audio")
async def analyze_audio_endpoint(
    language: str = Form("Spanish"),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    content_type = file.content_type or ""
    suffix = Path(file.filename or "").suffix.lower()
    if content_type not in SUPPORTED_AUDIO_TYPES and suffix not in {".wav", ".mp3", ".webm"}:
        raise HTTPException(status_code=400, detail="Upload a .wav or .mp3 audio file.")

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Upload or record audio before analyzing.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Audio file is too large for the MVP limit.")

    try:
        analysis = await analyze_audio(audio, file.filename or "recording.webm", content_type, language)
    except InferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    save_analysis(db, user, analysis)
    return analysis


@app.get("/api/review/history")
async def review_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list_history(db, user)


@app.get("/api/review/history/{analysis_id}")
async def review_analysis(analysis_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    analysis = get_analysis(db, user, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


@app.get("/api/review/vocabulary")
async def review_vocabulary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list_vocabulary(db, user)


@app.post("/api/review/vocabulary")
async def save_vocabulary(request: SaveVocabularyRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = save_vocabulary_selection(db, user, request)
    if entry is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return entry
