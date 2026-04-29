import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.config import get_model_name, get_ollama_base_url, get_provider, load_env


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

    def test_provider_accepts_ollama(self) -> None:
        with patch.dict(os.environ, {"PROVIDER": "ollama"}, clear=True):
            self.assertEqual(get_provider(), "ollama")

    def test_provider_rejects_unknown_value(self) -> None:
        with patch.dict(os.environ, {"PROVIDER": "nope"}, clear=True):
            with self.assertRaisesRegex(ValueError, "PROVIDER must be google or ollama"):
                get_provider()

    def test_ollama_base_url_strips_trailing_slash(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://localhost:11434/"}, clear=True):
            self.assertEqual(get_ollama_base_url(), "http://localhost:11434")


if __name__ == "__main__":
    unittest.main()
