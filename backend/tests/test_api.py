import asyncio
import os
import tempfile
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

TEST_DB_DIR = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(TEST_DB_DIR.name) / 'test.db'}"

from backend.app.db import SessionLocal, init_db
from backend.app.inference import (
    _normalize_analysis_payload,
    _speech_api_endpoint,
    _transcribe_with_google_speech_sync,
    _vllm_audio_messages,
    analyze_audio,
)
from backend.app.main import app
from backend.app.models import AnalysisRecord, AuthToken, User, VocabularySave, VocabularyTerm
from backend.app.schemas import TextAnalysisResponse
from backend.app.storage import analysis_response


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
            db.query(VocabularySave).delete()
            db.query(VocabularyTerm).delete()
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

    def test_analysis_schema_can_rehydrate_non_spanish_language(self) -> None:
        response = analysis_response(
            AnalysisRecord(
                id=123,
                user_id=1,
                input_type="text",
                language="French",
                source_text="Bonjour.",
                english_translation="Hello.",
                syntax_json='[{"feature": "Greeting", "explanation": "A simple greeting."}]',
                vocabulary_json='[{"term": "Bonjour", "lemma": "bonjour", "part_of_speech": "interj.", "gender": "n/a", "definition": "hello", "level": "A1"}]',
                notes_json="[]",
            )
        )

        self.assertIsInstance(response, TextAnalysisResponse)
        self.assertEqual(response.language, "French")

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

    def test_demo_auth_creates_isolated_user_session(self) -> None:
        first = self.request("POST", "/api/auth/demo")
        second = self.request("POST", "/api/auth/demo")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["username"], "Demo")
        self.assertEqual(second.json()["username"], "Demo")
        self.assertNotEqual(first.json()["token"], second.json()["token"])

        first_headers = {"Authorization": f"Bearer {first.json()['token']}"}
        second_headers = {"Authorization": f"Bearer {second.json()['token']}"}
        analysis_response = self.request(
            "POST",
            "/api/analyze/text",
            headers=first_headers,
            json={"language": "Spanish", "text": "Hola."},
        )
        self.assertEqual(analysis_response.status_code, 200)

        first_history = self.request("GET", "/api/review/history", headers=first_headers)
        second_history = self.request("GET", "/api/review/history", headers=second_headers)

        self.assertEqual(len(first_history.json()), 1)
        self.assertEqual(second_history.json(), [])

        with SessionLocal() as db:
            demo_users = db.query(User).filter(User.username.like("demo_%")).all()
            self.assertEqual(len(demo_users), 2)

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
        analysis_response = self.request(
            "POST",
            "/api/analyze/text",
            headers=headers,
            json={"language": "Spanish", "text": "Cuando era nino, sonaba con viajar."},
        )
        analysis = analysis_response.json()

        history_response = self.request("GET", "/api/review/history", headers=headers)
        vocab_response = self.request("GET", "/api/review/vocabulary", headers=headers)

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(vocab_response.status_code, 200)
        self.assertEqual(len(history_response.json()), 1)
        self.assertEqual(vocab_response.json(), [])

        word = analysis["vocabulary"][0]
        save_response = self.request(
            "POST",
            "/api/review/vocabulary",
            headers=headers,
            json={
                "analysis_id": analysis["analysis_id"],
                "term": word["term"],
                "lemma": word["lemma"],
                "part_of_speech": word["part_of_speech"],
                "gender": word["gender"],
                "definition": word["definition"],
                "level": word["level"],
            },
        )
        vocab_response = self.request("GET", "/api/review/vocabulary", headers=headers)

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(vocab_response.json()[0]["lemma"], word["lemma"])
        self.assertEqual(vocab_response.json()[0]["part_of_speech"], word["part_of_speech"])
        self.assertEqual(vocab_response.json()[0]["gender"], word["gender"])
        self.assertEqual(vocab_response.json()[0]["occurrences"][0]["surface_form"], word["term"])

    def test_vllm_audio_builds_multimodal_chat_request(self) -> None:
        messages = _vllm_audio_messages(b"fake-audio", "recording.webm", "audio/webm", "Spanish")
        content = messages[0]["content"]

        self.assertEqual(content[1]["type"], "input_audio")
        self.assertEqual(content[1]["input_audio"]["format"], "webm")
        self.assertTrue(content[1]["input_audio"]["data"])

    def test_model_payload_normalizes_common_schema_aliases(self) -> None:
        payload = {
            "ipa_transcript": ["ˈola"],
            "orthographic_transcript": ["Hola", "mundo."],
            "english_translation": ["Hello", "world."],
            "vocabulary": [
                {"part_of_speech": "v", "gender": "NA", "level": "a1"},
                {"part_of_speech": "prep", "gender": "m/f", "level": "n/a"},
            ]
        }

        normalized = _normalize_analysis_payload(payload)

        self.assertEqual(normalized["ipa_transcript"], "ˈola")
        self.assertEqual(normalized["orthographic_transcript"], "Hola mundo.")
        self.assertEqual(normalized["english_translation"], "Hello world.")
        self.assertEqual(normalized["vocabulary"][0]["part_of_speech"], "v.")
        self.assertEqual(normalized["vocabulary"][0]["gender"], "n/a")
        self.assertEqual(normalized["vocabulary"][0]["level"], "A1")
        self.assertEqual(normalized["vocabulary"][1]["part_of_speech"], "prep.")
        self.assertEqual(normalized["vocabulary"][1]["gender"], "m./f.")
        self.assertEqual(normalized["vocabulary"][1]["level"], "N/A")

    def test_google_speech_requires_project(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(Exception, "GOOGLE_CLOUD_PROJECT"):
                _transcribe_with_google_speech_sync(b"fake-audio")

    def test_speech_api_endpoint_uses_regional_endpoint_for_us_and_eu(self) -> None:
        self.assertEqual(_speech_api_endpoint("us"), "us-speech.googleapis.com")
        self.assertEqual(_speech_api_endpoint("eu"), "eu-speech.googleapis.com")
        self.assertIsNone(_speech_api_endpoint("global"))

    def test_google_audio_fallback_uses_asr_transcript(self) -> None:
        class FakeModels:
            @staticmethod
            def generate_content(model, contents):
                class Response:
                    text = """
                    {
                      "input_type": "audio",
                      "language": "Spanish",
                      "orthographic_transcript": "ignored",
                      "ipa_transcript": "ˈola ˈmundo",
                      "english_translation": "Hello, world.",
                      "syntax_analysis": [{"feature": "Greeting", "explanation": "Uses hola as a greeting."}],
                      "vocabulary": [{"term": "Hola", "lemma": "hola", "part_of_speech": "interj.", "gender": "n/a", "definition": "hello", "level": "A1"}],
                      "notes": []
                    }
                    """

                return Response()

        class FakeClient:
            models = FakeModels()

        with (
            patch.dict(
                os.environ,
                {
                    "PROVIDER": "google",
                    "GOOGLE_API_KEY": "test-key",
                    "MODEL": "gemma-test",
                },
                clear=True,
            ),
            patch("backend.app.inference._google_client", return_value=FakeClient()),
            patch("backend.app.inference._transcribe_with_google_speech", return_value="Hola, mundo."),
        ):
            analysis = asyncio.run(analyze_audio(b"fake-audio", "recording.webm", "audio/webm", "Spanish"))

        self.assertEqual(analysis.orthographic_transcript, "Hola, mundo.")
        self.assertEqual(analysis.ipa_transcript, "ˈola ˈmundo")
        self.assertEqual(analysis.notes, [])


if __name__ == "__main__":
    unittest.main()
