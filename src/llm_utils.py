"""Text/JSON generation with live model discovery and cross-provider fallback.

Use the providers' REST APIs so new model IDs don't require an SDK upgrade.
"""
import json
import os
import re
import time
from urllib.parse import quote

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "groq": "https://api.groq.com/openai/v1",
}
DEFAULT_MODELS = {
    "gemini": ("gemini-flash-latest", "gemini-flash-lite-latest"),
    "groq": ("openai/gpt-oss-120b", "openai/gpt-oss-20b"),
}
# Expire exclusions so a long-running process can recover after access changes.
_UNAVAILABLE = {}
MAX_MODEL_ATTEMPTS = 8


class LLMError(RuntimeError):
    def __init__(self, message, status=None, code=""):
        super().__init__(message)
        self.status = status
        self.code = code


def _request(provider, key, method, path, **kwargs):
    headers = ({"x-goog-api-key": key} if provider == "gemini"
               else {"Authorization": f"Bearer {key}"})
    try:
        response = requests.request(
            method, BASE_URLS[provider] + path, headers=headers,
            timeout=(10, 90), **kwargs,
        )
    except requests.RequestException:
        # Do not expose request headers, keys or prompt content in logs.
        raise LLMError(f"{provider}: network request failed") from None
    try:
        data = response.json()
    except ValueError:
        raise LLMError(f"{provider}: non-JSON response", response.status_code) from None
    if not response.ok:
        error = data.get("error", {})
        code = str(error.get("code", error.get("status", ""))) if isinstance(error, dict) else ""
        # Only include structured status, never the server's echoed request.
        raise LLMError(f"{provider}: HTTP {response.status_code}", response.status_code, code)
    return data


def _is_text_model(provider, model):
    name = model.get("name", "").removeprefix("models/") if provider == "gemini" else model.get("id", "")
    if provider == "gemini":
        return ("generateContent" in model.get("supportedGenerationMethods", [])
                and re.fullmatch(r"gemini-(?:\d+(?:\.\d+)?-(?:flash(?:-lite)?|pro)(?:-\d{3})?|(?:flash(?:-lite)?|pro)-latest)", name) is not None)
    # Groq's catalog does not expose chat/JSON capability flags. Restrict discovery
    # to general-purpose text families; exclude guard, speech and tool-only models.
    return (model.get("active", True)
            and name.startswith(("openai/gpt-oss-", "llama-", "meta-llama/llama-", "qwen/"))
            and not any(word in name.lower() for word in (
                "guard", "safeguard", "prompt", "tool", "preview", "audio", "speech")))


def _discover_models(provider, key):
    models, page_token = [], None
    seen_tokens = set()
    while True:
        params = {"pageSize": 1000} if provider == "gemini" else {}
        if page_token:
            params["pageToken"] = page_token
        data = _request(provider, key, "GET", "/models", params=params)
        models.extend(data.get("models" if provider == "gemini" else "data", []))
        page_token = data.get("nextPageToken") if provider == "gemini" else None
        if not page_token or page_token in seen_tokens:
            break
        seen_tokens.add(page_token)
    models = [m for m in models if _is_text_model(provider, m)]
    if provider == "gemini":
        def rank(model):
            name = model["name"]
            version = re.search(r"gemini-(\d+)(?:\.(\d+))?", name)
            return ("flash" in name, tuple(int(v or 0) for v in version.groups()) if version else (0, 0), name)
        models.sort(key=rank, reverse=True)
        return [m["name"].removeprefix("models/") for m in models]
    models.sort(key=lambda m: (m.get("created", 0), m["id"]), reverse=True)
    return [m["id"] for m in models]


def _candidates(provider, key):
    preferred = os.getenv(f"{provider.upper()}_MODEL", "").strip().removeprefix("models/")
    fallbacks = os.getenv(f"{provider.upper()}_FALLBACK_MODELS", "")
    configured = [preferred] + [m.strip().removeprefix("models/") for m in fallbacks.split(",")]
    try:
        discovered = _discover_models(provider, key)
    except LLMError as error:
        print(f"      [LLM] {provider} model discovery unavailable ({error}); trying configured defaults.")
        discovered = []
    # Explicit choices first, then rolling/known defaults and newly discovered models.
    return list(dict.fromkeys(m for m in configured + list(DEFAULT_MODELS[provider]) + discovered if m))


def _generate(provider, key, model, system_prompt, user_prompt, response_format):
    if provider == "gemini":
        config = {"temperature": 0.7, "maxOutputTokens": 8192 if "MASTERCLASS" in user_prompt else 4096}
        if response_format == "json":
            config["responseMimeType"] = "application/json"
        data = _request(provider, key, "POST", f"/models/{quote(model, safe='')}:generateContent", json={
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": config,
        })
        candidates = data.get("candidates", [])
        candidate = candidates[0] if candidates else {}
        if candidate.get("finishReason") != "STOP":
            raise LLMError("gemini: incomplete or blocked response")
        text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []) if not p.get("thought"))
    else:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.7,
            "max_completion_tokens": 6000 if "MASTERCLASS" in user_prompt else 2000,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}
            payload["messages"][0]["content"] += "\nReturn valid JSON. If an array is requested, wrap it in a JSON object."
        data = _request(provider, key, "POST", "/chat/completions", json=payload)
        choices = data.get("choices", [])
        choice = choices[0] if choices else {}
        if choice.get("finish_reason") != "stop":
            raise LLMError("groq: incomplete or blocked response")
        text = choice.get("message", {}).get("content") or ""
    text = text.strip()
    if not text:
        raise LLMError(f"{provider}: empty response")
    if response_format == "json":
        try:
            json.loads(text)
        except ValueError:
            raise LLMError(f"{provider}: invalid JSON response") from None
    return text


def call_llm(system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
    """Try compatible models, then the other provider. Never rewrite source/config."""
    if response_format not in ("text", "json"):
        raise ValueError("response_format must be 'text' or 'json'")
    providers = ["gemini", "groq"] if os.getenv("PREFER_GEMINI", "false").lower() == "true" else ["groq", "gemini"]
    failures = []
    for provider in providers:
        key = os.getenv("GOOGLE_API_KEY" if provider == "gemini" else "GROQ_API_KEY")
        if not key:
            failures.append(f"{provider}: API key not configured")
            continue
        attempts = 0
        for model in _candidates(provider, key):
            cache_key = (provider, model)
            if _UNAVAILABLE.get(cache_key, 0) > time.monotonic():
                continue
            if attempts >= MAX_MODEL_ATTEMPTS:
                break
            attempts += 1
            try:
                result = _generate(provider, key, model, system_prompt, user_prompt, response_format)
                print(f"      [LLM] Using {provider}/{model}")
                return result
            except LLMError as error:
                failures.append(f"{provider}/{model}: {error}")
                print(f"      [LLM] {provider}/{model} failed ({error}); trying fallback.")
                if error.status in (404, 410) or error.code in ("model_decommissioned", "model_not_found"):
                    _UNAVAILABLE[cache_key] = time.monotonic() + 3600
                elif error.status in (401, 403):
                    # Authentication/permission failures are not model deprecations.
                    break
    raise LLMError("All LLM providers failed. " + "; ".join(failures))
