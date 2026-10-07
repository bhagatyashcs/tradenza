"""
Universal AI Gateway - Tradenza
Provides a unified client for LLM providers:
- Google Gemini (Gemini 1.5 Flash / Pro)
- OpenAI (GPT-4o / GPT-4o-mini)
- Local Ollama (Self-hosted offline LLMs)
- Seamless fallback to offline heuristic engine.
Uses Python's standard library urllib for zero external dependencies and fast startup.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AIGateway:
    """
    Universal LLM Interface.
    Translates common prompt messages into provider-specific REST APIs.
    """

    DEFAULT_NVIDIA_MODEL = "deepseek-ai/deepseek-v4.1-flash"
    DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
    DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
    DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
    DEFAULT_OLLAMA_MODEL = "llama3"

    @classmethod
    def generate_chat_response(
        cls,
        provider: str,
        api_key: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        ollama_endpoint: str = "http://localhost:11434",
        nvidia_base_url: Optional[str] = None,
        timeout_seconds: int = 15
    ) -> Tuple[bool, str]:
        """
        Generates a response from the chosen AI provider.
        Returns: (success: bool, response_text: str)
        """
        provider = (provider or "nvidia").strip().lower()

        if provider == "offline":
            return False, "Offline mode selected."

        if provider in ["nvidia", "deepseek"]:
            return cls._call_nvidia(
                api_key=api_key,
                messages=messages,
                model=model or cls.DEFAULT_NVIDIA_MODEL,
                base_url=nvidia_base_url or cls.DEFAULT_NVIDIA_BASE_URL,
                timeout=timeout_seconds
            )

        if provider == "gemini":
            return cls._call_gemini(
                api_key=api_key,
                messages=messages,
                model=model or cls.DEFAULT_GEMINI_MODEL,
                timeout=timeout_seconds
            )

        if provider == "openai":
            return cls._call_openai(
                api_key=api_key,
                messages=messages,
                model=model or cls.DEFAULT_OPENAI_MODEL,
                timeout=timeout_seconds
            )

        if provider in ["ollama", "local"]:
            return cls._call_ollama(
                endpoint=ollama_endpoint,
                messages=messages,
                model=model or cls.DEFAULT_OLLAMA_MODEL,
                timeout=timeout_seconds
            )

        return False, f"Unsupported AI provider: {provider}"

    # ------------------------------------------------------------------
    # 0. NVIDIA NIM REST API (OpenAI-compatible DeepSeek inference)
    # ------------------------------------------------------------------

    @classmethod
    def _call_nvidia(
        cls,
        api_key: str,
        messages: List[Dict[str, str]],
        model: str,
        timeout: int,
        base_url: str = DEFAULT_NVIDIA_BASE_URL
    ) -> Tuple[bool, str]:
        if not api_key:
            return False, "NVIDIA NIM API key is not configured."

        endpoint = f"{base_url.rstrip('/')}/chat/completions"

        # Normalize roles
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role in ["aura", "model"]:
                role = "assistant"
            formatted_messages.append({
                "role": role,
                "content": msg.get("content", "")
            })

        payload = {
            "model": model or cls.DEFAULT_NVIDIA_MODEL,
            "messages": formatted_messages,
            "temperature": 0.6,
            "max_tokens": 1024
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            choices = result.get("choices") or []
            if choices:
                text = choices[0].get("message", {}).get("content", "")
                if text:
                    return True, text.strip()

            return False, "No completion choices returned by NVIDIA NIM."

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.warning("NVIDIA NIM HTTP Error %s: %s", e.code, err_body[:200])
            return False, f"NVIDIA NIM API returned error HTTP {e.code}"
        except Exception as e:
            logger.warning("NVIDIA NIM request exception: %s", str(e))
            return False, f"NVIDIA NIM connection failed: {str(e)}"

    # ------------------------------------------------------------------
    # 1. Google Gemini REST API
    # ------------------------------------------------------------------

    @classmethod
    def _call_gemini(
        cls,
        api_key: str,
        messages: List[Dict[str, str]],
        model: str,
        timeout: int
    ) -> Tuple[bool, str]:
        if not api_key:
            return False, "Gemini API key is not configured."

        # Separate system instruction from conversation turns
        system_text = ""
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_text += content + "\n\n"
            elif role in ["user", "human"]:
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role in ["assistant", "model", "aura"]:
                contents.append({"role": "model", "parts": [{"text": content}]})

        if not contents:
            return False, "No user content provided to Gemini."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
                "topP": 0.95
            }
        }
        if system_text.strip():
            payload["systemInstruction"] = {
                "parts": [{"text": system_text.strip()}]
            }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            candidates = result.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    return True, parts[0]["text"].strip()

            return False, "No response candidates returned by Gemini."

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.warning("Gemini HTTP Error %s: %s", e.code, err_body[:200])
            return False, f"Gemini API returned error HTTP {e.code}"
        except Exception as e:
            logger.warning("Gemini request exception: %s", str(e))
            return False, f"Gemini connection failed: {str(e)}"

    # ------------------------------------------------------------------
    # 2. OpenAI REST API
    # ------------------------------------------------------------------

    @classmethod
    def _call_openai(
        cls,
        api_key: str,
        messages: List[Dict[str, str]],
        model: str,
        timeout: int
    ) -> Tuple[bool, str]:
        if not api_key:
            return False, "OpenAI API key is not configured."

        url = "https://api.openai.com/v1/chat/completions"

        # Normalize roles
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role in ["aura", "model"]:
                role = "assistant"
            formatted_messages.append({
                "role": role,
                "content": msg.get("content", "")
            })

        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            choices = result.get("choices") or []
            if choices:
                text = choices[0].get("message", {}).get("content", "")
                if text:
                    return True, text.strip()

            return False, "No completion choices returned by OpenAI."

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.warning("OpenAI HTTP Error %s: %s", e.code, err_body[:200])
            return False, f"OpenAI API returned error HTTP {e.code}"
        except Exception as e:
            logger.warning("OpenAI request exception: %s", str(e))
            return False, f"OpenAI connection failed: {str(e)}"

    # ------------------------------------------------------------------
    # 3. Local Ollama REST API
    # ------------------------------------------------------------------

    @classmethod
    def _call_ollama(
        cls,
        endpoint: str,
        messages: List[Dict[str, str]],
        model: str,
        timeout: int
    ) -> Tuple[bool, str]:
        endpoint = (endpoint or "http://localhost:11434").rstrip("/")
        url = f"{endpoint}/api/chat"

        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role in ["aura", "model"]:
                role = "assistant"
            formatted_messages.append({
                "role": role,
                "content": msg.get("content", "")
            })

        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": False
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            content = result.get("message", {}).get("content", "")
            if content:
                return True, content.strip()

            return False, "Empty message response from Ollama."

        except Exception as e:
            logger.warning("Ollama connection exception: %s", str(e))
            return False, f"Local Ollama connection failed: {str(e)}"
