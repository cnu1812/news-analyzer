"""Offline regression tests: no API keys, paid calls, or podcast publishing."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import llm_utils as llm


def gemini_model(name):
    return {"name": f"models/{name}", "supportedGenerationMethods": ["generateContent"]}


def gemini_response(text="hello", reason="STOP"):
    return {"candidates": [{"finishReason": reason, "content": {"parts": [{"text": text}]}}]}


def groq_response(text="hello"):
    return {"choices": [{"finish_reason": "stop", "message": {"content": text}}]}


class LLMTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"GOOGLE_API_KEY": "test-google", "GROQ_API_KEY": "test-groq", "PREFER_GEMINI": "true"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        llm._UNAVAILABLE.clear()

    @patch.object(llm, "_request")
    def test_retired_override_falls_back_and_is_not_retried(self, request):
        os.environ["GEMINI_MODEL"] = "gemini-retired"
        def respond(provider, key, method, path, **kwargs):
            if method == "GET":
                return {"models": []}
            if "gemini-retired" in path:
                raise llm.LLMError("gone", 404)
            return gemini_response()
        request.side_effect = respond
        self.assertEqual(llm.call_llm("system", "user"), "hello")
        self.assertEqual(llm.call_llm("system", "user"), "hello")
        self.assertEqual(sum("gemini-retired" in c.args[3] for c in request.call_args_list), 1)

    @patch.object(llm, "_request")
    def test_all_known_defaults_retire_future_model_discovered(self, request):
        def respond(provider, key, method, path, **kwargs):
            if method == "GET":
                return {"models": [gemini_model("gemini-9.2-flash"), gemini_model("gemini-9.10-flash")]}
            if "gemini-9.10-flash" in path:
                return gemini_response("future")
            raise llm.LLMError("gone", 404)
        request.side_effect = respond
        self.assertEqual(llm.call_llm("s", "u"), "future")

    @patch.object(llm, "_request")
    def test_groq_future_model_discovery(self, request):
        os.environ["PREFER_GEMINI"] = "false"
        def respond(provider, key, method, path, **kwargs):
            if method == "GET":
                return {"data": [{"id": "openai/gpt-oss-999b", "created": 999}]}
            if kwargs["json"]["model"] == "openai/gpt-oss-999b":
                return groq_response()
            raise llm.LLMError("retired", 400, "model_decommissioned")
        request.side_effect = respond
        self.assertEqual(llm.call_llm("s", "u"), "hello")
        self.assertEqual(len(llm._UNAVAILABLE), 2)

    @patch.object(llm, "_request")
    def test_pagination_and_specialized_model_filtering(self, request):
        request.side_effect = [
            {"models": [gemini_model("gemini-8.0-flash-image")], "nextPageToken": "next"},
            {"models": [gemini_model("gemini-8.0-flash"), gemini_model("gemini-8.0-pro-preview"), {"name": "models/gemini-8.0-pro", "supportedGenerationMethods": ["embedContent"]}]},
        ]
        self.assertEqual(llm._discover_models("gemini", "key"), ["gemini-8.0-flash"])
        self.assertEqual(request.call_args.kwargs["params"]["pageToken"], "next")
        for name in ("whisper-large-v3", "openai/gpt-oss-safeguard-20b", "meta-llama/llama-guard-4-12b", "groq/compound", "qwen/preview"):
            self.assertFalse(llm._is_text_model("groq", {"id": name}))

    @patch.object(llm, "_request")
    def test_discovery_outage_does_not_block_generation(self, request):
        request.side_effect = [llm.LLMError("outage", 503), gemini_response()]
        self.assertEqual(llm.call_llm("s", "u"), "hello")

    @patch.object(llm, "_request")
    def test_auth_failure_switches_provider_without_retiring_model(self, request):
        def respond(provider, key, method, path, **kwargs):
            if method == "GET":
                return {}
            if provider == "gemini":
                raise llm.LLMError("unauthorized", 401)
            return groq_response()
        request.side_effect = respond
        self.assertEqual(llm.call_llm("s", "u"), "hello")
        self.assertEqual(sum(c.args[0] == "gemini" and c.args[2] == "POST" for c in request.call_args_list), 1)
        self.assertFalse(llm._UNAVAILABLE)

    @patch.object(llm, "_request")
    def test_json_parameters_validation_and_fallback(self, request):
        request.side_effect = [{"models": []}, gemini_response("bad json"), gemini_response('["approved"]')]
        self.assertEqual(llm.call_llm("s", "u", "json"), '["approved"]')
        self.assertEqual(request.call_args.kwargs["json"]["generationConfig"]["responseMimeType"], "application/json")

    @patch.object(llm, "_request")
    def test_groq_json_contract_and_long_script_budget(self, request):
        request.return_value = groq_response('{"approved_titles": []}')
        llm._generate("groq", "key", "model", "s", "MASTERCLASS", "json")
        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["max_completion_tokens"], 6000)
        self.assertIn("JSON object", payload["messages"][0]["content"])

    @patch.object(llm, "_request")
    def test_truncated_and_empty_responses_rejected(self, request):
        for response in (gemini_response("partial", "MAX_TOKENS"), gemini_response("")):
            request.return_value = response
            with self.assertRaises(llm.LLMError):
                llm._generate("gemini", "key", "model", "s", "u", "text")

    @patch.object(llm, "_request")
    def test_rate_limits_are_not_cached_as_deprecation(self, request):
        request.side_effect = [{}, llm.LLMError("rate limit", 429), gemini_response()]
        self.assertEqual(llm.call_llm("s", "u"), "hello")
        self.assertFalse(llm._UNAVAILABLE)

    @patch.object(llm, "_request")
    def test_missing_keys_and_bounded_exhaustion(self, request):
        os.environ.pop("GOOGLE_API_KEY")
        os.environ.pop("GROQ_API_KEY")
        with self.assertRaisesRegex(llm.LLMError, "API key not configured"):
            llm.call_llm("s", "u")
        request.assert_not_called()
        os.environ["GOOGLE_API_KEY"] = "key"
        with patch.object(llm, "_candidates", return_value=[f"model-{i}" for i in range(100)]):
            request.side_effect = llm.LLMError("failed", 503)
            with self.assertRaisesRegex(llm.LLMError, "All LLM providers failed"):
                llm.call_llm("s", "u")
            self.assertEqual(request.call_count, llm.MAX_MODEL_ATTEMPTS)

    @patch.object(llm, "_discover_models", return_value=[])
    def test_explicit_configuration_and_deduplication(self, discover):
        os.environ["GEMINI_MODEL"] = "models/custom"
        os.environ["GEMINI_FALLBACK_MODELS"] = "custom, second, , gemini-flash-latest"
        self.assertEqual(llm._candidates("gemini", "key"), ["custom", "second", "gemini-flash-latest", "gemini-flash-lite-latest"])

    @patch.object(llm.requests, "request")
    def test_http_auth_timeouts_and_redacted_error(self, request):
        request.return_value.ok = False
        request.return_value.status_code = 400
        request.return_value.json.return_value = {"error": {"code": "model_decommissioned", "message": "secret key and prompt"}}
        with self.assertRaises(llm.LLMError) as caught:
            llm._request("gemini", "secret", "GET", "/models")
        self.assertEqual(caught.exception.code, "model_decommissioned")
        self.assertNotIn("secret", str(caught.exception))
        self.assertEqual(request.call_args.kwargs["headers"], {"x-goog-api-key": "secret"})
        self.assertEqual(request.call_args.kwargs["timeout"], (10, 90))


if __name__ == "__main__":
    unittest.main()
