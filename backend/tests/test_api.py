import asyncio
import uuid
import unittest
from unittest.mock import patch

import httpx

from backend.app.db import SessionLocal, init_db
from backend.app.inference import _vllm_audio_messages
from backend.app.main import app
from backend.app.models import AnalysisRecord, AuthToken, User, VocabularyOccurrence


class GemmaGlotApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patch = patch.dict(
            "os.environ",
            {"PROVIDER": "google", "GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""},
        )
        self.env_patch.start()
        init_db()
        self._clear_db()

    def tearDown(self) -> None:
        self._clear_db()
        self.env_patch.stop()

    def _clear_db(self) -> None:
        with SessionLocal() as db:
            db.query(VocabularyOccurrence).delete()
            db.query(AnalysisRecord).delete()
            db.query(AuthToken).delete()
            db.query(User).delete()
            db.commit()

    def request(self, method: str, url: str, **kwargs):
        async def make_request():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(make_request())

    def auth_headers(self) -> dict[str, str]:
        username = f"user_{uuid.uuid4().hex[:12]}"
        response = self.request(
            "POST",
            "/api/auth/register",
            json={"username": username, "password": "password123"},
        )
        self.assertEqual(response.status_code, 201)
        return {"Authorization": f"Bearer {response.json()['token']}"}

    def test_health(self) -> None:
        response = self.request("GET", "/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_text_analysis_returns_schema(self) -> None:
        headers = self.auth_headers()
        response = self.request(
            "POST",
            "/api/analyze/text",
            headers=headers,
            json={
                "language": "Spanish",
                "text": "Cuando era nino, sonaba con viajar.",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["input_type"], "text")
        self.assertEqual(payload["language"], "Spanish")
        self.assertTrue(payload["syntax_analysis"])
        self.assertTrue(payload["vocabulary"])

    def test_audio_analysis_accepts_browser_recording(self) -> None:
        headers = self.auth_headers()
        response = self.request(
            "POST",
            "/api/analyze/audio",
            headers=headers,
            data={"language": "Spanish"},
            files={"file": ("recording.webm", b"fake-audio", "audio/webm")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["input_type"], "audio")
        self.assertIn("orthographic_transcript", payload)
        self.assertIn("ipa_transcript", payload)

    def test_audio_analysis_rejects_unsupported_file(self) -> None:
        headers = self.auth_headers()
        response = self.request(
            "POST",
            "/api/analyze/audio",
            headers=headers,
            data={"language": "Spanish"},
            files={"file": ("notes.txt", b"not-audio", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)

    def test_analysis_requires_authentication(self) -> None:
        response = self.request(
            "POST",
            "/api/analyze/text",
            json={"language": "Spanish", "text": "Hola."},
        )

        self.assertEqual(response.status_code, 401)

    def test_review_history_and_vocabulary_use_saved_analysis(self) -> None:
        headers = self.auth_headers()
        self.request(
            "POST",
            "/api/analyze/text",
            headers=headers,
            json={"language": "Spanish", "text": "Cuando era nino, sonaba con viajar."},
        )

        history_response = self.request("GET", "/api/review/history", headers=headers)
        vocab_response = self.request("GET", "/api/review/vocabulary", headers=headers)

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(vocab_response.status_code, 200)
        self.assertEqual(len(history_response.json()), 1)
        self.assertTrue(vocab_response.json())

    def test_vllm_audio_builds_multimodal_chat_request(self) -> None:
        messages = _vllm_audio_messages(b"fake-audio", "recording.webm", "audio/webm", "Spanish")
        content = messages[0]["content"]

        self.assertEqual(content[1]["type"], "input_audio")
        self.assertEqual(content[1]["input_audio"]["format"], "webm")
        self.assertTrue(content[1]["input_audio"]["data"])


if __name__ == "__main__":
    unittest.main()
