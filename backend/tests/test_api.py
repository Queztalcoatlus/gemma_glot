import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


class GemmaGlotApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patch = patch.dict(
            "os.environ",
            {"PROVIDER": "google", "GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""},
        )
        self.env_patch.start()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.env_patch.stop()

    def test_health(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_text_analysis_returns_schema(self) -> None:
        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.post(
            "/api/analyze/audio",
            data={"language": "Spanish"},
            files={"file": ("notes.txt", b"not-audio", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)

    def test_ollama_audio_returns_clear_limitation(self) -> None:
        with patch.dict("os.environ", {"PROVIDER": "ollama"}, clear=False):
            response = self.client.post(
                "/api/analyze/audio",
                data={"language": "Spanish"},
                files={"file": ("recording.webm", b"fake-audio", "audio/webm")},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("Ollama does not accept raw audio", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
