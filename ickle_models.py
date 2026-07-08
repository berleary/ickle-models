#!/usr/bin/env python3
"""MCP server exposing a LiteLLM gateway as model-calling tools for Claude.

Lets Claude (e.g. in Claude Code) consult any model reachable through a single
LiteLLM gateway -- local Ollama models and any cloud model behind OpenRouter
(OpenAI, Perplexity, DeepSeek, Gemini, ...) -- through one endpoint and one key,
instead of juggling per-provider API keys.

Three tools are exposed:
  - list_models(): discover every callable model id (raw gateway list)
  - describe_models(model): the *approved-models catalogue* -- which models to
    use for what, their strengths/weaknesses, and (crucially) how to structure
    queries per family (system-prompt handling, reasoning-model quirks,
    temperature norms, JSON-mode support). Read this before call_model so you
    are not guessing query structure.
  - call_model(model, prompt, system, max_tokens): send a prompt to any of them

Configuration (environment variables):
  ICKLE_BASE_URL      Gateway base URL (default http://localhost:4000)
  LITELLM_MASTER_KEY  Gateway auth key. If unset, read from a key file.
  ICKLE_MCP_ENV       Path to a file containing a LITELLM_MASTER_KEY=... line
                      (default ~/.config/ickle-mcp/env)
  ICKLE_CATALOGUE     Path to the approved-models catalogue YAML
                      (default: data/approved-models.yaml next to this file)

Transport: stdio (spawned as a subprocess by the MCP client).
"""
import json
import os
import urllib.error
import urllib.request

from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("ICKLE_BASE_URL", "http://localhost:4000")
CATALOGUE_PATH = os.environ.get(
    "ICKLE_CATALOGUE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "approved-models.yaml"),
)


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


def _load_catalogue() -> dict:
    """Load the approved-models catalogue YAML.

    Kept dependency-light: uses PyYAML if available, else a JSON sidecar
    (data/approved-models.json), else returns an error marker. The server
    still starts and list_models/call_model work regardless.
    """
    try:
        import yaml  # type: ignore
        with open(CATALOGUE_PATH) as f:
            return yaml.safe_load(f) or {}
    except ModuleNotFoundError:
        json_path = os.path.splitext(CATALOGUE_PATH)[0] + ".json"
        try:
            with open(json_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return {"_error": "PyYAML not installed and no JSON sidecar found",
                    "_path": CATALOGUE_PATH}
    except FileNotFoundError:
        return {"_error": "catalogue file not found", "_path": CATALOGUE_PATH}
    except Exception as e:  # noqa: BLE001
        return {"_error": f"failed to load catalogue: {e}", "_path": CATALOGUE_PATH}


@mcp.tool()
def list_models() -> list[str]:
    """List every model id callable through the gateway (local + cloud).

    This is the *raw* gateway list -- valid `model` values for call_model, with
    no guidance. For which model to use and how to prompt it, call
    describe_models() (the curated, evidence-based approved-models catalogue).
    """
    try:
        return [m["id"] for m in _request("/v1/models", timeout=30).get("data", [])]
    except Exception as e:  # noqa: BLE001 - surface the error to the model
        return [f"[error listing models: {e}]"]


@mcp.tool()
def describe_models(model: str = "") -> dict:
    """The approved-models catalogue: which model to use, and how to prompt it.

    Read this before call_model so you are not guessing query structure --
    prompting conventions differ across families (DeepSeek/Qwen/GLM/OpenAI/...):
    system-prompt handling, reasoning-model quirks (e.g. DeepSeek R1 think
    tags), temperature norms, and JSON-mode support all vary.

    Args:
        model: optional. If given (exact id, or a substring / family name like
            "deepseek"), returns just the matching catalogue entry (or entries)
            plus the family prompting guide. If omitted, returns the full
            catalogue: metadata, the per-family prompting guide, and every
            model entry.

    Returns a dict with keys: `meta` (reviewed date, provenance, how to read),
    `families` (prompting conventions keyed by family), and `models` (approved
    entries with use_cases / strengths / weaknesses / cost_speed / status /
    provenance). Models with no bakeoff evidence are marked status:
    "unassessed" -- treat their notes as untested.
    """
    cat = _load_catalogue()
    if "_error" in cat:
        return cat
    if not model:
        return cat
    q = model.lower()
    families = cat.get("families", {})
    entries = cat.get("models", [])
    exact = [m for m in entries if m.get("id", "").lower() == q]
    matches = exact or [m for m in entries
                        if q in m.get("id", "").lower() or q == m.get("family", "").lower()]
    fam_keys = {m.get("family") for m in matches if m.get("family")}
    if q in families:
        fam_keys.add(q)
    guide = {k: families[k] for k in fam_keys if k in families}
    if not matches:
        return {"query": model, "matches": [],
                "note": ("no catalogue entry matches; call list_models() for the raw id "
                         "list. Unlisted models are unassessed -- prompt conservatively "
                         "and consult the family guide below if the family is known."),
                "families": guide or families,
                "meta": cat.get("meta", {})}
    return {"query": model, "matches": matches, "families": guide, "meta": cat.get("meta", {})}


@mcp.tool()
def call_model(model: str, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Send a prompt to any model available via the gateway and return its reply.

    Use this to consult another model mid-task -- e.g. a web-search model for
    fresh facts, or a specific frontier/local model for a second opinion. Call
    describe_models() first if you are unsure how to structure the query for the
    target model's family.

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
