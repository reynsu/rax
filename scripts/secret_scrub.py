"""Best-effort scrubbing for secret-shaped substrings in error messages.

Used wherever exception text or third-party API response bodies are
serialized to disk or shown in the report (`scripts/cross_llm_eval.py`,
`scripts/judge_panel.py`). Catches the usual prefixes the major LLM SDKs
embed in error messages; not a substitute for not capturing secrets in
the first place.
"""
from __future__ import annotations

import re
from typing import List

# Order matters: longer / more-specific prefixes first.
_SECRET_PATTERNS: List[re.Pattern] = [
    re.compile(r"sk-ant-(?:api|admin)\d+-[A-Za-z0-9_\-]{20,}"),  # Anthropic
    re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"),                  # OpenAI project keys
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),                       # OpenAI legacy
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),                      # Google API key
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),                         # GitHub PAT
    re.compile(r"gh[opsu]_[A-Za-z0-9]{30,}"),                    # GitHub variants
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9_\-\.=+/]{20,}"),
    re.compile(r"(?i)Authorization:\s*[^\s]+"),
    re.compile(r"x-api-key:\s*[^\s]+", re.I),
]


REPLACEMENT = "[REDACTED]"


def scrub(text: str) -> str:
    """Return `text` with secret-shaped substrings replaced by [REDACTED]."""
    if not text:
        return text
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub(REPLACEMENT, out)
    return out
