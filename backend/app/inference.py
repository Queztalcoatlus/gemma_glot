import asyncio
import base64
import json
import urllib.error
import urllib.request
from typing import Any

from backend.app.config import get_api_key, get_model_name, get_provider, get_vllm_api_key, get_vllm_base_url, load_env
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
  "vocabulary": [{"term": "surface form from input", "lemma": "dictionary form", "part_of_speech": "n.|v.|adj.|adv.|pron.|prep.|conj.|interj.|expr.|other", "gender": "m.|f.|m./f.|n/a", "definition": "string", "level": "A1|A2|B1|B2|C1|C2|N/A"}],
  "notes": ["string"]
}
Prioritize useful syntax patterns and learner-worthy vocabulary. For Spanish verbs, use the infinitive as lemma; for nouns/adjectives, use the singular masculine lemma when appropriate. Include part_of_speech for every vocabulary item. Use gender only for nouns and noun-like entries; use "n/a" otherwise. Be concise.
"""


AUDIO_SYSTEM_PROMPT = """
You are GemmaGlot, a concise Spanish audio transcription and language-learning analyst.
Base the IPA transcription on the audio signal, not on a generic pronunciation inferred from the orthographic transcript.
For orthographic_transcript, use standard Spanish spelling for the intended words, not eye-dialect or phonetic spelling. For example, if the speaker realizes "llamo" as [ʃamo], write "Me llamo Julio" in orthographic_transcript and preserve [ʃ] only in ipa_transcript.
Return only valid JSON matching this schema:
{
  "input_type": "audio",
  "language": "Spanish",
  "orthographic_transcript": "string",
  "ipa_transcript": "string",
  "english_translation": "string",
  "syntax_analysis": [{"feature": "string", "explanation": "string"}],
  "vocabulary": [{"term": "surface form from input", "lemma": "dictionary form", "part_of_speech": "n.|v.|adj.|adv.|pron.|prep.|conj.|interj.|expr.|other", "gender": "m.|f.|m./f.|n/a", "definition": "string", "level": "A1|A2|B1|B2|C1|C2|N/A"}],
  "notes": ["string"]
}
For ipa_transcript, preserve the speaker's heard dialect features when audible, including seseo/distincion, yeismo or lleismo, /s/ aspiration or deletion, final consonant weakening, intervocalic /d/ weakening or deletion, /x/ or /h/ realizations, /r/ and /rr/ variants, and major vowel/consonant reductions. Do not normalize these to textbook Castilian or textbook Latin American pronunciation unless that is what the audio contains.
Use a broad-but-faithful IPA transcription. Include narrow allophones only when confidence is high. If the audio is unclear or the model cannot reliably hear a dialect feature, use a conservative broad transcription and add a note about the uncertainty.
For Spanish verbs, use the infinitive as lemma; for nouns/adjectives, use the singular masculine lemma when appropriate. Include part_of_speech for every vocabulary item. Use gender only for nouns and noun-like entries; use "n/a" otherwise.
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


async def _vllm_chat(messages: list[dict[str, Any]]) -> str:
    url = f"{get_vllm_base_url()}/chat/completions"
    payload = json.dumps(
        {
            "model": get_model_name(),
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1800,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    api_key = get_vllm_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        return await asyncio.to_thread(_send_vllm_request, request)
    except urllib.error.URLError as exc:
        raise InferenceError(
            "Could not reach vLLM. Start the vLLM OpenAI-compatible server, check VLLM_BASE_URL, then retry."
        ) from exc


def _send_vllm_request(request: urllib.request.Request) -> str:
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))

    try:
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise InferenceError("vLLM returned an unexpected response.") from exc

    if not isinstance(text, str) or not text.strip():
        raise InferenceError("vLLM returned an empty response.")
    return text


def _vllm_text_messages(prompt: str) -> list[dict[str, Any]]:
    return [{"role": "user", "content": prompt}]


def _vllm_audio_messages(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    language: str,
) -> list[dict[str, Any]]:
    audio_format = _audio_format(filename, content_type)
    audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"{AUDIO_SYSTEM_PROMPT}\n\nTarget language: {language}. Analyze this audio file: {filename}",
                },
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_base64,
                        "format": audio_format,
                    },
                },
            ],
        }
    ]


def _audio_format(filename: str, content_type: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in {"wav", "mp3", "webm", "mpeg", "mpga", "m4a", "ogg", "flac"}:
        return suffix

    content_type_formats = {
        "audio/wav": "wav",
        "audio/wave": "wav",
        "audio/x-wav": "wav",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/webm": "webm",
    }
    return content_type_formats.get(content_type, "wav")


async def analyze_text(source_text: str, language: str) -> TextAnalysisResponse:
    if language != SUPPORTED_LANGUAGE:
        raise InferenceError(f"{language} is not supported yet.")

    provider = get_provider()
    if provider == "vllm":
        prompt = f"{TEXT_SYSTEM_PROMPT}\n\nTarget language: {language}\nInput:\n{source_text}"
        try:
            payload = _extract_json(await _vllm_chat(_vllm_text_messages(prompt)))
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
    if provider == "vllm":
        try:
            payload = _extract_json(await _vllm_chat(_vllm_audio_messages(audio_bytes, filename, content_type, language)))
            return AudioAnalysisResponse.model_validate(payload)
        except Exception as exc:
            raise InferenceError(str(exc)) from exc

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
                "lemma": "sonar",
                "part_of_speech": "v.",
                "gender": "n/a",
                "definition": 'Imperfect form of "sonar", used for dreams or recurring hopes.',
                "level": "A2",
            },
            {
                "term": "imagine",
                "lemma": "imaginar",
                "part_of_speech": "v.",
                "gender": "n/a",
                "definition": 'Preterite form of "imaginar", meaning "I imagined."',
                "level": "B1",
            },
            {
                "term": "forma de ver",
                "lemma": "forma de ver",
                "part_of_speech": "expr.",
                "gender": "f.",
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
                "lemma": "sonar",
                "part_of_speech": "v.",
                "gender": "n/a",
                "definition": 'Imperfect form of "sonar", used for recurring or background dreams.',
                "level": "A2",
            },
            {
                "term": "viajar",
                "lemma": "viajar",
                "part_of_speech": "v.",
                "gender": "n/a",
                "definition": "To travel; a high-frequency infinitive.",
                "level": "A1",
            },
            {
                "term": "America Latina",
                "lemma": "America Latina",
                "part_of_speech": "n.",
                "gender": "f.",
                "definition": "Latin America; useful regional/geographic phrase.",
                "level": "A2",
            },
        ],
        notes=[f"Mock analysis for {filename}; configure GOOGLE_API_KEY to use Gemma."],
    )
