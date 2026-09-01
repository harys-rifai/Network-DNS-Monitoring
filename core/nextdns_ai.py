"""OpenRouter AI client for the Network-DNS-Monitoring web clone.

Uses the OpenRouter API with the ``openrouter/free`` router so that a free
model is automatically selected at random from the pool of currently available
free models. The API key is read from the ``NEXTDNS_OPENROUTER_API_KEY``
environment variable (never committed to source).

No extra dependencies beyond ``requests`` (stdlib HTTP could work, but
``requests`` handles timeouts and JSON cleanly).
"""

import json
import os

import requests

API_BASE = os.environ.get("NEXTDNS_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
API_KEY = os.environ.get("NEXTDNS_OPENROUTER_API_KEY", "")
DEFAULT_MODEL = os.environ.get("NEXTDNS_OPENROUTER_MODEL", "openrouter/free")
DEFAULT_TIMEOUT = 30


def available():
    """Return True if the OpenRouter API key is configured."""
    return bool(API_KEY)


def list_free_models(timeout=DEFAULT_TIMEOUT):
    """Fetch the OpenRouter model catalog and return models priced free.

    Returns a list of dicts with ``id``, ``name`` and ``context`` for every
    model whose prompt and completion prices are both ``"0"``.
    """
    headers = {"Authorization": "Bearer %s" % API_KEY}
    url = "%s/models" % API_BASE
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    free = []
    for m in data.get("data", []):
        pricing = m.get("pricing", {})
        if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
            free.append({
                "id": m.get("id"),
                "name": m.get("name"),
                "context": m.get("context_length"),
            })
    return free


def chat(messages, model=DEFAULT_MODEL, timeout=DEFAULT_TIMEOUT, stream=False):
    """Send a chat conversation to OpenRouter and return the assistant reply.

    ``messages`` is a list of ``{"role": "...", "content": "..."}`` dicts.
    When ``model`` is ``openrouter/free`` (the default) the API automatically
    routes to a random free model.

    Returns a dict with ``content``, ``model`` and ``error`` keys.
    """
    if not API_KEY:
        return {"content": None, "model": model,
                "error": "NEXTDNS_OPENROUTER_API_KEY is not set."}

    headers = {
        "Authorization": "Bearer %s" % API_KEY,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/nextdns/nextdns",
        "X-Title": "Network-DNS-Monitoring Web Clone",
    }
    body = {"model": model, "messages": messages}
    url = "%s/chat/completions" % API_BASE

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout, stream=stream)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return {"content": None, "model": model, "error": "Request to OpenRouter timed out."}
    except requests.exceptions.ConnectionError:
        return {"content": None, "model": model, "error": "Cannot reach OpenRouter API."}
    except requests.exceptions.HTTPError as e:
        return {"content": None, "model": model, "error": "OpenRouter API error: %s" % e}

    if stream:
        return _stream(resp, model)

    data = resp.json()
    choice = data.get("choices", [{}])[0]
    msg = choice.get("message", {})
    return {
        "content": msg.get("content", "").strip(),
        "model": data.get("model", model),
        "error": None,
    }


def _stream(resp, model):
    """Yield streaming content chunks from a streaming response."""
    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue
        choice = chunk.get("choices", [{}])[0]
        delta = choice.get("delta", {})
        content = delta.get("content")
        if content:
            yield {"content": content, "model": model, "error": None}
