#!/usr/bin/env python3
"""MCP server exposing a LiteLLM gateway as model-calling tools for Claude.

Lets Claude (e.g. in Claude Code) consult any model reachable through a single
LiteLLM gateway -- local Ollama models and any cloud model behind OpenRouter
(OpenAI, Perplexity, DeepSeek, Gemini, ...) -- through one endpoint and one key,
instead of juggling per-provider API keys.

Two tools are exposed:
  - list_models(): discover every callable model id
  - call_model(model, prompt, system, max_tokens): send a prompt to any of them

Configuration (environment variables):
  ICKLE_BASE_URL      Gateway base URL (default http://localhost:4000)
  LITELLM_MASTER_KEY  Gateway auth key. If unset, read from a key file.
  ICKLE_MCP_ENV       Path to a file containing a LITELLM_MASTER_KEY=... line
                      (default ~/.config/ickle-mcp/env)

Transport: stdio (spawned as a subprocess by the MCP client).
"""
import json
import os
import urllib.error
import urllib.request

from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("ICKLE_BASE_URL", "http://localhost:4000")


def _load_key() -> str:
    key = os.environ.get("LITELLM_MASTER_KEY")
    if key:
        return key
    env_path = os.environ.get("ICKLE_MCP_ENV", os.path.expanduser("~/.config/ickle-mcp/env"))
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("LITELLM_MASTER_KEY="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""


KEY = _load_key()
mcp = FastMCP("ickle-models")


def _request(path: str, payload: dict | None = None, timeout: int = 120):
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers,
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


@mcp.tool()
def list_models() -> list[str]:
    """List every model id callable through the gateway (local + cloud).
    Call this first to discover valid `model` values for call_model."""
    try:
        return [m["id"] for m in _request("/v1/models", timeout=30).get("data", [])]
    except Exception as e:  # noqa: BLE001 - surface the error to the model
        return [f"[error listing models: {e}]"]


@mcp.tool()
def call_model(model: str, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Send a prompt to any model available via the gateway and return its reply.

    Use this to consult another model mid-task -- e.g. a web-search model for
    fresh facts, or a specific frontier/local model for a second opinion.

    Args:
        model: a model id from list_models(), e.g. "openrouter/openai/gpt-4o",
            "openrouter/perplexity/sonar", "openrouter/deepseek/deepseek-chat",
            or a local model such as "qwen2.5:3b".
        prompt: the user message to send.
        system: optional system prompt.
        max_tokens: response cap (default 1024).
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = _request("/v1/chat/completions",
                        {"model": model, "messages": messages, "max_tokens": max_tokens})
        return resp["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"[gateway error {e.code}: {e.read().decode(errors='replace')[:300]}]"
    except Exception as e:  # noqa: BLE001
        return f"[error calling {model}: {e}]"


if __name__ == "__main__":
    mcp.run()
