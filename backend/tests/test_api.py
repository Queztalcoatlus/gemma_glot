import asyncio
import unittest
from unittest.mock import patch

import httpx

from backend.app.inference import _vllm_audio_messages
from backend.app.main import app


class GemmaGlotApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patch = patch.dict(
            "os.environ",
            {"PROVIDER": "google", "GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""},
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()

    def request(self, method: str, url: str, **kwargs):
        async def make_request():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(make_request())

    def test_health(self) -> None:
        response = self.request("GET", "/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_text_analysis_returns_schema(self) -> None:
        response = self.request(
            "POST",
            "/api/analyze/text",
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
        response = self.request(
            "POST",
            "/api/analyze/audio",
            data={"language": "Spanish"},
            files={"file": ("recording.webm", b"fake-audio", "audio/webm")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["input_type"], "audio")
        self.assertIn("orthographic_transcript", payload)
        self.assertIn("ipa_transcript", payload)

    def test_audio_analysis_rejects_unsupported_file(self) -> None:
        response = self.request(
            "POST",
            "/api/analyze/audio",
            data={"language": "Spanish"},
            files={"file": ("notes.txt", b"not-audio", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)

    def test_vllm_audio_builds_multimodal_chat_request(self) -> None:
        messages = _vllm_audio_messages(b"fake-audio", "recording.webm", "audio/webm", "Spanish")
        content = messages[0]["content"]

        self.assertEqual(content[1]["type"], "input_audio")
        self.assertEqual(content[1]["input_audio"]["format"], "webm")
        self.assertTrue(content[1]["input_audio"]["data"])


if __name__ == "__main__":
    unittest.main()
