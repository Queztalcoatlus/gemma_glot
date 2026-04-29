import asyncio
import json
import urllib.error
import urllib.request
from typing import Any

from backend.app.config import get_api_key, get_model_name, get_ollama_base_url, get_provider, load_env
from backend.app.schemas import AudioAnalysisResponse, TextAnalysisResponse


load_env()
SUPPORTED_LANGUAGE = "Spanish"


TEXT_SYSTEM_PROMPT = """
You are GemmaGlot, a concise language-learning analyst.
Return only valid JSON matching this schema:
{
  "input_type": "text",
  "language": "Spanish",
  "source_text": "string",
  "english_translation": "string",
  "syntax_analysis": [{"feature": "string", "explanation": "string"}],
  "vocabulary": [{"term": "string", "definition": "string", "level": "A1|A2|B1|B2|C1|C2"}],
  "notes": ["string"]
}
Prioritize useful syntax patterns and learner-worthy vocabulary. Be concise.
"""


AUDIO_SYSTEM_PROMPT = """
You are GemmaGlot, a concise Spanish audio transcription and language-learning analyst.
Return only valid JSON matching this schema:
{
  "input_type": "audio",
  "language": "Spanish",
  "orthographic_transcript": "string",
  "ipa_transcript": "string",
  "english_translation": "string",
  "syntax_analysis": [{"feature": "string", "explanation": "string"}],
  "vocabulary": [{"term": "string", "definition": "string", "level": "A1|A2|B1|B2|C1|C2"}],
  "notes": ["string"]
}
Use readable IPA with helpful major allophones when confidence is high.
"""


class InferenceError(RuntimeError):
    """Raised when the configured model provider cannot produce an analysis."""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise InferenceError("The model did not return a JSON object.")
    return json.loads(cleaned[start : end + 1])


def _google_client():
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        from google import genai
    except ImportError as exc:
        raise InferenceError("google-genai is not installed.") from exc
    return genai.Client(api_key=api_key)


async def _ollama_generate(prompt: str) -> str:
    url = f"{get_ollama_base_url()}/api/generate"
    payload = json.dumps(
        {
            "model": get_model_name(),
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        return await asyncio.to_thread(_send_ollama_request, request)
    except urllib.error.URLError as exc:
        raise InferenceError(
            "Could not reach Ollama. Start Ollama, pull the configured MODEL, then retry."
        ) from exc


def _send_ollama_request(request: urllib.request.Request) -> str:
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    text = payload.get("response")
    if not isinstance(text, str) or not text.strip():
        raise InferenceError("Ollama returned an empty response.")
    return text


async def analyze_text(source_text: str, language: str) -> TextAnalysisResponse:
    if language != SUPPORTED_LANGUAGE:
        raise InferenceError(f"{language} is not supported yet.")

    provider = get_provider()
    if provider == "ollama":
        prompt = f"{TEXT_SYSTEM_PROMPT}\n\nTarget language: {language}\nInput:\n{source_text}"
        try:
            payload = _extract_json(await _ollama_generate(prompt))
            return TextAnalysisResponse.model_validate(payload)
        except Exception as exc:
            raise InferenceError(str(exc)) from exc

    client = _google_client()
    if client is None:
        return _mock_text_response(source_text)

    prompt = f"{TEXT_SYSTEM_PROMPT}\n\nTarget language: {language}\nInput:\n{source_text}"
    try:
        response = client.models.generate_content(model=get_model_name(), contents=prompt)
        payload = _extract_json(response.text or "")
        return TextAnalysisResponse.model_validate(payload)
    except Exception as exc:
        raise InferenceError(str(exc)) from exc


async def analyze_audio(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    language: str,
) -> AudioAnalysisResponse:
    if language != SUPPORTED_LANGUAGE:
        raise InferenceError(f"{language} is not supported yet.")

    provider = get_provider()
    if provider == "ollama":
        raise InferenceError(
            "Ollama does not accept raw audio through this app yet. Use text analysis with Ollama, "
            "or switch PROVIDER=google with an audio-capable model for audio input."
        )

    client = _google_client()
    if client is None:
        return _mock_audio_response(filename)

    try:
        from google.genai import types

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=content_type)
        response = client.models.generate_content(
            model=get_model_name(),
            contents=[
                AUDIO_SYSTEM_PROMPT,
                f"Target language: {language}. Analyze this audio file: {filename}",
                audio_part,
            ],
        )
        payload = _extract_json(response.text or "")
        return AudioAnalysisResponse.model_validate(payload)
    except Exception as exc:
        raise InferenceError(str(exc)) from exc


def _mock_text_response(source_text: str) -> TextAnalysisResponse:
    return TextAnalysisResponse(
        language="Spanish",
        source_text=source_text,
        english_translation=(
            "When I was a child, I always dreamed of traveling through Latin America, "
            "but I never imagined that learning another language would change my way "
            "of seeing the world so much."
        ),
        syntax_analysis=[
            {
                "feature": "Imperfect tense for background",
                "explanation": '"Era" and "sonaba" describe ongoing past states and repeated experiences.',
            },
            {
                "feature": "Subordinate noun clause",
                "explanation": '"Que aprender otro idioma cambiaria..." functions as the thing the speaker did not imagine.',
            },
            {
                "feature": "Infinitive as subject",
                "explanation": '"Aprender otro idioma" works as a noun phrase meaning "learning another language."',
            },
        ],
        vocabulary=[
            {
                "term": "sonaba",
                "definition": 'Imperfect form of "sonar", used for dreams or recurring hopes.',
                "level": "A2",
            },
            {
                "term": "imagine",
                "definition": 'Preterite form of "imaginar", meaning "I imagined."',
                "level": "B1",
            },
            {
                "term": "forma de ver",
                "definition": "Expression meaning a way of seeing, understanding, or interpreting something.",
                "level": "B1",
            },
        ],
        notes=["Mock analysis shown because no Google API key is configured."],
    )


def _mock_audio_response(filename: str) -> AudioAnalysisResponse:
    return AudioAnalysisResponse(
        language="Spanish",
        orthographic_transcript="Cuando era nino, siempre sonaba con viajar por America Latina.",
        ipa_transcript="/'kwando 'eɾa 'niɲo, 'sjempɾe so'ɲaβa kom bja'xaɾ poɾ a'meɾika la'tina/",
        english_translation="When I was a child, I always dreamed of traveling through Latin America.",
        syntax_analysis=[
            {
                "feature": "Imperfect tense",
                "explanation": '"Era" and "sonaba" describe background states and repeated past experience.',
            },
            {
                "feature": "Infinitive after preposition",
                "explanation": '"Con viajar" uses an infinitive after "con" to express the content of the dream.',
            },
        ],
        vocabulary=[
            {
                "term": "sonaba",
                "definition": 'Imperfect form of "sonar", used for recurring or background dreams.',
                "level": "A2",
            },
            {"term": "viajar", "definition": "To travel; a high-frequency infinitive.", "level": "A1"},
            {
                "term": "America Latina",
                "definition": "Latin America; useful regional/geographic phrase.",
                "level": "A2",
            },
        ],
        notes=[f"Mock analysis for {filename}; configure GOOGLE_API_KEY to use Gemma."],
    )
