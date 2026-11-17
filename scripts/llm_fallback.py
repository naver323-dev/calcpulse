#!/usr/bin/env python3
"""Free-tier LLM chain: Gemini -> Groq -> OpenRouter (:free models).

The daily pipelines cannot afford to lose a day because one free tier ran out of
quota at 10:15. This module puts every provider behind one call and walks them in
order, so a 429 on Gemini becomes a Groq generation instead of a skipped guide.

    import llm_fallback
    draft, label = llm_fallback.chat_json(system_prompt, user_prompt)
    text,  label = llm_fallback.chat_text(system_prompt, user_prompt)

What counts as a failure, and what happens next:

    quota (429, or 403 with a quota body)  -> next model, then next provider
    bad key (401/403 without quota)        -> next provider, reported if nothing works
    retired model / endpoint (404/410)     -> next model, then next provider
    5xx / timeout / network                -> one retry, then next provider
    200 with unusable JSON                 -> next model, then next provider

Nothing here spends money: every tier is a provider free tier, and Groq and the
OpenRouter :free models need no card.
GitHub Models was retired on 2026-07-30; its request path stays in the module so an
OpenAI-compatible endpoint can take that slot (GITHUB_MODELS_ENDPOINT) without code
changes. A provider with no credential is skipped, so the same code runs in a shell
where only one key exists and in CI where several do.

Environment
    GEMINI_API_KEY             Google AI Studio key (free tier)
    GEMINI_MODEL               optional, comma separated model list
    GROQ_API_KEY               Groq Cloud key (free tier, no card)
    GROQ_MODEL                 optional, comma separated model list
    GROQ_BASE_URL              optional, default https://api.groq.com/openai/v1
    OPENROUTER_API_KEY         third tier; ":free" models cost nothing and need no card
    OPENROUTER_MODEL           optional, comma separated model list
    OPENROUTER_BASE_URL        optional, default https://openrouter.ai/api/v1
    CEREBRAS_API_KEY           optional extra tier (Cerebras gates access behind a saved card)
    CEREBRAS_MODEL             optional, comma separated model list
    CEREBRAS_BASE_URL          optional, default https://api.cerebras.ai/v1
    GITHUB_MODELS_TOKEN        optional; service retired 2026-07-30, kept as a spare endpoint
    GITHUB_MODELS_ENDPOINT     optional, default https://models.github.ai/inference
    LLM_PROVIDERS              optional, comma separated order, e.g. "gemini,groq"
    LLM_USER_AGENT             optional override for the client user agent

Command line
    python3 scripts/llm_fallback.py --check     # which tiers answer right now
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any, Callable

from urllib import error as urlerror
from urllib import request as urlrequest

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GROQ_BASE = "https://api.groq.com/openai/v1"
DEFAULT_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_CEREBRAS_BASE = "https://api.cerebras.ai/v1"
DEFAULT_GITHUB_MODELS_BASE = "https://models.github.ai/inference"

# Free-tier models that answer with plain text or JSON. Groq's gpt-oss models carry
# json_mode + a 131k context window, which is what the 800-1700 word guides need.
DEFAULT_GEMINI_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite")
DEFAULT_GROQ_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
DEFAULT_OPENROUTER_MODELS = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "dots-studio/dots-3-note-preview:free",
    "google/gemma-4-26b-a4b-it:free",
)
DEFAULT_CEREBRAS_MODELS = ("gpt-oss-120b", "qwen-3.8-27b")
DEFAULT_GITHUB_MODELS = ("openai/gpt-4o-mini", "deepseek/DeepSeek-V3-0324")

PROVIDER_NAMES = ("gemini", "groq", "openrouter", "cerebras", "github-models")
DEFAULT_PROVIDERS = ("gemini", "groq", "openrouter")
LABEL_PREFIX = {
    "gemini": "",
    "groq": "groq:",
    "openrouter": "openrouter:",
    "cerebras": "cerebras:",
    "github-models": "github:",
}

# 0 is a timeout or dropped connection, which deserves the same single retry as a 5xx.
RETRY_STATUS = (0, 500, 502, 503, 504)

# Groq sits behind Cloudflare, which answers the default Python-urllib user agent with
# HTTP 403 (error 1010) before the request ever reaches the API. Send our own name.
USER_AGENT = "calcpulse-pipeline/1.0 (+https://calcpulse.pages.dev)"


class ProviderError(RuntimeError):
    """One provider refused one request. The chain decides what that means."""

    def __init__(self, provider: str, model: str, detail: str, status: int | None = None):
        super().__init__(f"{provider}/{model}: {detail}")
        self.provider = provider
        self.model = model
        self.detail = detail
        self.status = status

    @property
    def quota(self) -> bool:
        lowered = self.detail.lower()
        return self.status == 429 or (
            self.status in (402, 403)
            and any(word in lowered for word in ("quota", "resource_exhausted", "rate limit", "limit exceeded"))
        )

    @property
    def auth(self) -> bool:
        return self.status in (401, 403) and not self.quota

    @property
    def retired(self) -> bool:
        return self.status in (404, 410)


class QuotaExhausted(RuntimeError):
    """Every reachable tier said no for quota. Not a failure: nobody publishes today."""


class ChainFailed(RuntimeError):
    """Nothing usable came back and at least one tier failed for a reason worth seeing."""


# --------------------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------------------
def http_post(url: str, headers: dict[str, str], payload: dict, timeout: int = 180) -> tuple[int, str]:
    """POST JSON and return (status, body). HTTP errors come back as a status, not an exception."""
    body = json.dumps(payload).encode("utf-8")
    merged = {"User-Agent": os.environ.get("LLM_USER_AGENT") or USER_AGENT, **headers}
    request = urlrequest.Request(url, data=body, headers=merged, method="POST")
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urlerror.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urlerror.URLError, TimeoutError, OSError) as exc:
        # A dropped connection or a read timeout has no HTTP status. Report it as status 0
        # instead of letting a raw exception escape and take the whole run with it.
        return 0, f"network error: {exc}"


Transport = Callable[[str, dict, dict, int], "tuple[int, str]"]


# --------------------------------------------------------------------------------------
# response parsing
# --------------------------------------------------------------------------------------
def parse_json_object(text: str) -> dict:
    """Tolerate a fenced or chatty answer; refuse anything that is not a JSON object."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", (text or "").strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        # A model that wraps the object in a one-element list still answered; unwrap it.
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
            return value[0]
        raise ValueError("answer is not a JSON object")
    return value


def _gemini_text(body: str) -> str:
    data = json.loads(body)
    candidates = data.get("candidates") or []
    if not candidates:
        feedback = data.get("promptFeedback") or {}
        raise ValueError(f"no candidates (promptFeedback={json.dumps(feedback)[:200]})")
    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts if not part.get("thought"))
    if not text.strip():
        raise ValueError(f"empty candidate (finishReason={candidate.get('finishReason')})")
    return text


def _openai_text(body: str) -> str:
    data = json.loads(body)
    choices = data.get("choices") or []
    if not choices:
        raise ValueError(f"no choices ({json.dumps(data)[:200]})")
    message = choices[0].get("message") or {}
    text = message.get("content")
    if isinstance(text, list):  # some gateways return content parts
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
    if not (text or "").strip():
        raise ValueError(f"empty message (finish_reason={choices[0].get('finish_reason')})")
    return text


# --------------------------------------------------------------------------------------
# provider configuration
# --------------------------------------------------------------------------------------
def _models_from_env(env: dict, key: str, default: tuple[str, ...]) -> list[str]:
    raw = (env.get(key) or "").strip()
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()] or list(default)


def provider_config(provider: str, env: dict | None = None) -> dict | None:
    """Everything needed to call one tier, or None when it has no credential here."""
    env = os.environ if env is None else env
    if provider == "gemini":
        key = (env.get("GEMINI_API_KEY") or "").strip()
        if not key:
            return None
        return {
            "key": key,
            "models": _models_from_env(env, "GEMINI_MODEL", DEFAULT_GEMINI_MODELS),
            "url": lambda model: f"{GEMINI_BASE}/{model}:generateContent?key={key}",
        }
    if provider == "groq":
        key = (env.get("GROQ_API_KEY") or "").strip()
        if not key:
            return None
        base = (env.get("GROQ_BASE_URL") or DEFAULT_GROQ_BASE).rstrip("/")
        return {
            "key": key,
            "models": _models_from_env(env, "GROQ_MODEL", DEFAULT_GROQ_MODELS),
            "url": lambda model: f"{base}/chat/completions",
            # gpt-oss thinks before it answers and the thinking is billed as completion
            # tokens, so a tight budget produced empty content with finish_reason=length.
            # "medium" is what keeps the guide inside its 780-1700 word contract.
            "extra": {"reasoning_effort": (env.get("GROQ_REASONING_EFFORT") or "medium").strip()},
            # Free tier is 8K tokens/minute for gpt-oss; a smaller answer budget leaves
            # room for the prompt instead of turning the next request into a 429.
            "max_tokens_cap": 4096,
        }
    if provider == "openrouter":
        key = (env.get("OPENROUTER_API_KEY") or "").strip()
        if not key:
            return None
        base = (env.get("OPENROUTER_BASE_URL") or DEFAULT_OPENROUTER_BASE).rstrip("/")
        return {
            "key": key,
            "models": _models_from_env(env, "OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODELS),
            "url": lambda model: f"{base}/chat/completions",
        }
    if provider == "cerebras":
        key = (env.get("CEREBRAS_API_KEY") or "").strip()
        if not key:
            return None
        base = (env.get("CEREBRAS_BASE_URL") or DEFAULT_CEREBRAS_BASE).rstrip("/")
        return {
            "key": key,
            "models": _models_from_env(env, "CEREBRAS_MODEL", DEFAULT_CEREBRAS_MODELS),
            "url": lambda model: f"{base}/chat/completions",
            "extra": {"reasoning_effort": (env.get("CEREBRAS_REASONING_EFFORT") or "medium").strip()},
            "max_tokens_cap": 4096,
        }
    if provider == "github-models":
        token = (env.get("GITHUB_MODELS_TOKEN") or env.get("GITHUB_TOKEN") or "").strip()
        if not token:
            return None
        base = (env.get("GITHUB_MODELS_ENDPOINT") or DEFAULT_GITHUB_MODELS_BASE).rstrip("/")
        return {
            "key": token,
            "models": _models_from_env(env, "GITHUB_MODELS_MODEL", DEFAULT_GITHUB_MODELS),
            "url": lambda model: f"{base}/chat/completions",
            "max_tokens_cap": 4096,
        }
    raise ValueError(f"unknown provider {provider}")


def provider_order(env: dict | None = None) -> list[str]:
    """The tier order to walk. LLM_PROVIDERS can narrow or reorder it per run."""
    env = os.environ if env is None else env
    raw = (env.get("LLM_PROVIDERS") or "").strip()
    if not raw:
        return list(DEFAULT_PROVIDERS)
    order = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [name for name in order if name not in PROVIDER_NAMES]
    if unknown:
        raise ValueError(f"LLM_PROVIDERS has unknown tier(s): {', '.join(unknown)}")
    return order or list(DEFAULT_PROVIDERS)


def is_configured(env: dict | None = None) -> bool:
    """True when at least one tier of the order has a credential here."""
    return any(provider_config(name, env) for name in provider_order(env))


# --------------------------------------------------------------------------------------
# one request against one model
# --------------------------------------------------------------------------------------
def _request(
    provider: str,
    model: str,
    config: dict,
    system: str,
    user: str,
    *,
    json_mode: bool,
    temperature: float,
    max_tokens: int,
    timeout: int,
    transport: Transport,
    log: Callable[[str], None],
) -> str:
    url = config["url"](model)

    if provider == "gemini":
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.95,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        headers = {"Content-Type": "application/json"}
    else:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        payload = {"model": model, "messages": messages, "temperature": temperature}
        budget = min(max_tokens, config.get("max_tokens_cap") or max_tokens)
        payload["max_completion_tokens" if provider in ("groq", "cerebras") else "max_tokens"] = budget
        if model.startswith("openai/gpt-oss") or model.startswith("gpt-oss"):
            payload.update({key: value for key, value in (config.get("extra") or {}).items() if value})
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['key']}",
        }
        if provider == "github-models":
            headers["Accept"] = "application/vnd.github+json"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        if provider == "openrouter":
            # OpenRouter ranks usage by these optional headers; they carry no secret.
            headers["X-Title"] = config.get("title") or "free-llm-fallback"

    status, body = transport(url, headers, payload, timeout)

    if status == 0:
        raise ProviderError(provider, model, body[:300] or "no response", 0)

    if status == 400 and json_mode and provider != "gemini" and "response_format" in body.lower():
        # A model that cannot promise JSON still answers; drop the flag and let the
        # parser decide. The caller's validator is the real gate either way.
        log(f"  ~ {provider}/{model}: no json mode, retrying without response_format")
        payload.pop("response_format", None)
        status, body = transport(url, headers, payload, timeout)

    if status == 200:
        try:
            return _gemini_text(body) if provider == "gemini" else _openai_text(body)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError(provider, model, f"unusable response: {exc}", status) from exc

    detail = re.sub(r"\s+", " ", body or "")[:300]
    raise ProviderError(provider, model, f"HTTP {status}: {detail}", status)


# --------------------------------------------------------------------------------------
# the chain
# --------------------------------------------------------------------------------------
def chat(
    system: str,
    user: str,
    *,
    mode: str = "json",
    temperature: float = 0.7,
    max_tokens: int = 8192,
    timeout: int = 180,
    attempts: int = 2,
    providers: list[str] | tuple[str, ...] | None = None,
    env: dict | None = None,
    transport: Transport = http_post,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = lambda *_: None,
) -> tuple[Any, str]:
    """Walk Gemini -> Groq -> GitHub Models and return (value, label).

    value is a dict for mode="json" and a str for mode="text".
    label is the model that answered, e.g. "gemini-3.5-flash-lite" or
    "groq:openai/gpt-oss-120b", so the caller can record where a draft came from.
    """
    if mode not in ("json", "text"):
        raise ValueError("mode must be 'json' or 'text'")
    json_mode = mode == "json"
    env = os.environ if env is None else env
    order = list(providers or provider_order(env))

    errors: list[ProviderError] = []
    configured = 0
    tried = 0

    for provider in order:
        config = provider_config(provider, env)
        if config is None:
            log(f"  · {provider}: no credential, skipped")
            continue
        configured += 1
        for model in config["models"]:
            tried += 1
            for attempt in range(attempts):
                try:
                    text = _request(
                        provider,
                        model,
                        config,
                        system,
                        user,
                        json_mode=json_mode,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                        transport=transport,
                        log=log,
                    )
                except ProviderError as exc:
                    errors.append(exc)
                    log(f"  ! {exc}")
                    if exc.status in RETRY_STATUS and attempt < attempts - 1:
                        sleep(5 * (attempt + 1))
                        continue
                    break

                if not json_mode:
                    return text, f"{LABEL_PREFIX[provider]}{model}"
                try:
                    return parse_json_object(text), f"{LABEL_PREFIX[provider]}{model}"
                except (json.JSONDecodeError, ValueError) as exc:
                    errors.append(ProviderError(provider, model, f"not JSON: {exc}", None))
                    log(f"  ! {provider}/{model}: answer was not a JSON object ({exc})")
                    break
            # A provider whose key is refused or whose quota is spent will refuse every
            # model the same way; stop walking it instead of burning the whole list.
            if errors and errors[-1].provider == provider and (errors[-1].auth or errors[-1].quota):
                break

    if configured == 0:
        raise ChainFailed(
            "no LLM credential is set (GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY)"
        )

    quota_only = bool(errors) and all(error.quota or error.retired for error in errors)
    # One line per tier instead of the last three model attempts: when three models of the
    # same provider fail, the reason that matters (a rejected key) would be pushed out.
    first_by_provider: dict[str, ProviderError] = {}
    for error in errors:
        first_by_provider.setdefault(error.provider, error)
    summary = "; ".join(str(error) for error in first_by_provider.values()) or "no attempt made"
    if quota_only:
        raise QuotaExhausted(f"every free tier is out of quota ({tried} attempt(s)): {summary}")
    raise ChainFailed(f"every provider failed ({tried} attempt(s)): {summary}")


def chat_json(system: str, user: str, **kwargs) -> tuple[dict, str]:
    return chat(system, user, mode="json", **kwargs)


def chat_text(system: str, user: str, **kwargs) -> tuple[str, str]:
    return chat(system, user, mode="text", **kwargs)


# --------------------------------------------------------------------------------------
# command line: which tiers answer right now
# --------------------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    if "--check" not in argv:
        print(__doc__)
        return 1
    print("free-tier LLM check (no content is published)")
    code = 0
    for provider in provider_order():
        config = provider_config(provider)
        if config is None:
            print(f"  - {provider}: no credential, skipped")
            continue
        model = config["models"][0]
        try:
            text = _request(
                provider,
                model,
                config,
                "You are a health check.",
                "Reply with the single word OK.",
                json_mode=False,
                temperature=0.0,
                max_tokens=64,
                timeout=60,
                transport=http_post,
                log=print,
            )
            print(f"  ok {provider}/{model}: {text.strip()[:60]!r}")
        except ProviderError as exc:
            code = 1
            print(f"  ! {provider}/{model}: {exc}")
        except Exception as exc:  # noqa: BLE001 - one bad tier must not hide the others
            code = 1
            print(f"  ! {provider}/{model}: {type(exc).__name__}: {exc}")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
