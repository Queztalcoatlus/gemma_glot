from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.app.inference import InferenceError, analyze_audio, analyze_text


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


class TextAnalysisRequest(BaseModel):
    language: str = "Spanish"
    text: str = Field(min_length=1, max_length=12000)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "backend": "google-api-first"}


@app.post("/api/analyze/text")
async def analyze_text_endpoint(request: TextAnalysisRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Enter Spanish text to analyze.")

    try:
        return await analyze_text(text, request.language)
    except InferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/analyze/audio")
async def analyze_audio_endpoint(
    language: str = Form("Spanish"),
    file: UploadFile = File(...),
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
        return await analyze_audio(audio, file.filename or "recording.webm", content_type, language)
    except InferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
