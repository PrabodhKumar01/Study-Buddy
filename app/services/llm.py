"""Local LLM service for communicating with open-weight models via Ollama.

Connects to a locally running Ollama instance (defaulting to Llama 3)
and handles timeouts, connection failures, and missing models gracefully.
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)


class LLMService:
    """Service wrapper for communicating with a local Ollama LLM."""

    def __init__(
        self,
        model_name: str | None = None,
        ollama_url: str | None = None,
        timeout_seconds: float = 60.0,
    ):
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME", "llama3")
        self.ollama_url = (ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def is_available(self) -> bool:
        """Check if the local Ollama server is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.ollama_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a response from the local LLM.

        Args:
            prompt: The formatted user prompt including retrieved context.
            system_prompt: Optional system prompt to guide LLM behavior.

        Returns:
            The generated text answer, or a friendly error message if unavailable.
        """
        # 1. If a cloud API key is configured (recommended when deploying to Vercel/cloud), use it
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            return await self._call_openai_compatible(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_api_key,
                model=os.getenv("CLOUD_MODEL_NAME", "llama-3.1-8b-instant"),
                prompt=prompt,
                system_prompt=system_prompt,
            )

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            return await self._call_openai_compatible(
                base_url=base_url,
                api_key=openai_api_key,
                model=os.getenv("CLOUD_MODEL_NAME", "gpt-3.5-turbo"),
                prompt=prompt,
                system_prompt=system_prompt,
            )

        # 2. Otherwise default to local Ollama (100% offline local laptop usage)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            timeout_config = httpx.Timeout(self.timeout_seconds, connect=3.0)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()

                if response.status_code == 404:
                    return (
                        f"⚠️ Ollama model '{self.model_name}' was not found. "
                        f"Please run `ollama pull {self.model_name}` in your terminal."
                    )

                return (
                    f"⚠️ Local LLM returned an error (status {response.status_code}): {response.text}"
                )

        except httpx.ConnectError:
            is_vercel = os.getenv("VERCEL") == "1"
            if is_vercel:
                return (
                    "⚠️ Study Buddy is running in serverless mode (Vercel) without a cloud LLM configured. "
                    "To enable AI responses on Vercel, add a free 'GROQ_API_KEY' (or 'OPENAI_API_KEY') "
                    "in your Vercel Project Settings > Environment Variables. "
                    "Alternatively, run this project locally on your laptop with Ollama for 100% offline use."
                )
            logger.warning(f"Could not connect to Ollama at {self.ollama_url}")
            return (
                f"⚠️ Local LLM is not currently running. "
                f"Please start Ollama (`ollama serve`) and ensure '{self.model_name}' is pulled (`ollama pull {self.model_name}`)."
            )
        except httpx.TimeoutException:
            logger.warning("Local LLM request timed out.")
            return "⚠️ The local LLM took too long to respond. Your computer may be under heavy load or the model is too large for CPU memory."
        except Exception as exc:
            logger.error(f"Unexpected error calling local LLM: {exc}")
            return f"⚠️ An error occurred while communicating with the local LLM: {str(exc)}"

    async def _call_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Call an OpenAI-compatible cloud endpoint (e.g. Groq, OpenRouter, or OpenAI)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            timeout_config = httpx.Timeout(self.timeout_seconds, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                res = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                    return "No response generated by cloud model."
                return f"⚠️ Cloud AI provider returned an error ({res.status_code}): {res.text}"
        except httpx.TimeoutException:
            return "⚠️ Cloud AI request timed out. Please try again."
        except Exception as exc:
            return f"⚠️ Error communicating with Cloud AI provider: {str(exc)}"


# Singleton instance
llm_service = LLMService()
