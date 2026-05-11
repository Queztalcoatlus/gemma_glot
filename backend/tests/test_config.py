import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.config import (
    get_google_cloud_location,
    get_google_cloud_project,
    get_model_name,
    get_provider,
    get_speech_language_code,
    get_speech_model,
    get_vllm_api_key,
    get_vllm_base_url,
    get_vllm_timeout_seconds,
    load_env,
)


class ConfigTests(unittest.TestCase):
    def test_load_env_reads_key_value_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "# comment",
                        "GOOGLE_API_KEY=from-file",
                        'MODEL="gemma-4-test"',
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                load_env((env_file,))

                self.assertEqual(os.environ["GOOGLE_API_KEY"], "from-file")
                self.assertEqual(os.environ["MODEL"], "gemma-4-test")

    def test_load_env_does_not_override_shell_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("GOOGLE_API_KEY=from-file", encoding="utf-8")

            with patch.dict(os.environ, {"GOOGLE_API_KEY": "from-shell"}, clear=True):
                load_env((env_file,))

                self.assertEqual(os.environ["GOOGLE_API_KEY"], "from-shell")

    def test_model_name_uses_model_variable(self) -> None:
        with patch.dict(os.environ, {"MODEL": "new-name"}, clear=True):
            self.assertEqual(get_model_name(), "new-name")

    def test_model_name_uses_default_when_unset(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_model_name(), "gemma-4-26b-a4b-it")

    def test_provider_defaults_to_google(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_provider(), "google")

    def test_provider_accepts_vllm(self) -> None:
        with patch.dict(os.environ, {"PROVIDER": "vllm"}, clear=True):
            self.assertEqual(get_provider(), "vllm")

    def test_provider_rejects_unknown_value(self) -> None:
        with patch.dict(os.environ, {"PROVIDER": "nope"}, clear=True):
            with self.assertRaisesRegex(ValueError, "PROVIDER must be google or vllm"):
                get_provider()

    def test_vllm_base_url_strips_trailing_slash(self) -> None:
        with patch.dict(os.environ, {"VLLM_BASE_URL": "http://localhost:8001/v1/"}, clear=True):
            self.assertEqual(get_vllm_base_url(), "http://localhost:8001/v1")

    def test_vllm_api_key_is_optional(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(get_vllm_api_key())

    def test_vllm_timeout_defaults_to_cloud_run_friendly_value(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_vllm_timeout_seconds(), 300)

    def test_vllm_timeout_accepts_positive_integer(self) -> None:
        with patch.dict(os.environ, {"VLLM_TIMEOUT_SECONDS": "600"}, clear=True):
            self.assertEqual(get_vllm_timeout_seconds(), 600)

    def test_vllm_timeout_rejects_invalid_value(self) -> None:
        with patch.dict(os.environ, {"VLLM_TIMEOUT_SECONDS": "slow"}, clear=True):
            with self.assertRaisesRegex(ValueError, "VLLM_TIMEOUT_SECONDS must be an integer"):
                get_vllm_timeout_seconds()

    def test_google_speech_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(get_google_cloud_project())
            self.assertEqual(get_google_cloud_location(), "us")
            self.assertEqual(get_speech_language_code(), "es-US")
            self.assertEqual(get_speech_model(), "chirp_3")


if __name__ == "__main__":
    unittest.main()
