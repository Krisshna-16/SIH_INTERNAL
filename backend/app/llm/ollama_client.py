import os
import logging
import requests

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


class OllamaConnectionError(Exception):
    """Raised when the local Ollama LLM service is unreachable."""
    pass


class OllamaTimeoutError(Exception):
    """Raised when the local Ollama LLM service times out during generation."""
    pass


class OllamaClient:
    """
    Thin wrapper client connecting to the local Ollama HTTP API.
    Zero external cloud calls — 100% local, privacy-preserving inference.
    """

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.host = host.rstrip("/")
        self.model = model

    def generate_answer(self, prompt: str, timeout_seconds: int = 30) -> str:
        """
        Generates grounded response from local Ollama model.
        Temperature set to 0.1 for zero creative drift.
        """
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature to minimize creative drift & hallucination
            },
        }

        try:
            logger.info(f"Sending prompt to local Ollama model '{self.model}' at {url}...")
            response = requests.post(url, json=payload, timeout=timeout_seconds)
            response.raise_for_status()
            res_json = response.json()
            answer = res_json.get("response", "").strip()
            return answer
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"Failed to connect to local Ollama service at '{self.host}': {ce}")
            raise OllamaConnectionError(
                f"Local LLM service unavailable at {self.host}. Please start Ollama and pull model '{self.model}'."
            ) from ce
        except requests.exceptions.Timeout as te:
            logger.error(f"Ollama generation timed out after {timeout_seconds}s: {te}")
            raise OllamaTimeoutError(f"Local LLM generation timed out after {timeout_seconds} seconds.") from te
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise RuntimeError(f"Local LLM error: {str(e)}") from e
