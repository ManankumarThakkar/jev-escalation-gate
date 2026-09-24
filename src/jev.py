"""A minimal Jev client, standard library only.

One dependency-free file so the experiment can be reproduced with nothing but
Python and a key. The official SDKs (`@typesafe-ai/sdk`, the Python client) are
fine choices for application code; here a thin client keeps the request shape
visible, which matters when the point of the repository is that you can check
what was actually sent.

Endpoint note, because it affects how the latency numbers should be read:
a ``jv_live_`` key is issued by jevtypesafeai.com, a third-party metered proxy
over the official API. ``https://api.typesafe.ai/v1/systemone`` rejects it with
a 401. Anything measured through the proxy therefore includes a proxy hop, and
the latency figures in this repository are labelled accordingly. Set
``JEV_ENDPOINT`` to the official URL if you hold a TypeSafe key.
"""

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://jevtypesafeai.com/api/v1/decide"
OFFICIAL_ENDPOINT = "https://api.typesafe.ai/v1/systemone"

RETRYABLE = (429, 500, 502, 503, 529)


class JevError(RuntimeError):
    """Any failure that stops a call returning an answer."""


class Jev:
    def __init__(self, api_key: str | None = None, endpoint: str | None = None, timeout: int = 45):
        self._key = api_key or os.environ.get("JEV_API_KEY", "")
        if not self._key:
            raise JevError("JEV_API_KEY is not set")
        self._endpoint = endpoint or os.environ.get("JEV_ENDPOINT", DEFAULT_ENDPOINT)
        self._timeout = timeout

    def __repr__(self) -> str:
        # Never the key: this object ends up in tracebacks that get pasted into issues.
        return f"Jev(endpoint={self._endpoint!r})"

    @property
    def via_proxy(self) -> bool:
        return "jevtypesafeai.com" in self._endpoint

    def ask(self, state: str, questions: dict, *, retries: int = 3) -> dict:
        """One request. Returns the parsed body plus a measured wall-clock latency.

        Latency is measured around the HTTP call only, so it includes network
        and, on the proxy endpoint, the proxy. It is not a server-side figure
        and is never presented as one.
        """
        body = json.dumps({"state": state, "questions": questions}).encode()
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

        for attempt in range(retries):
            request = urllib.request.Request(self._endpoint, data=body, headers=headers, method="POST")
            started = time.perf_counter()
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    payload = json.loads(response.read())
                payload["_latency_ms"] = (time.perf_counter() - started) * 1000
                return payload
            except urllib.error.HTTPError as exc:
                if exc.code in RETRYABLE and attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                # The status only. A 401 body in particular tends to echo the
                # credential it just rejected.
                raise JevError(f"HTTP {exc.code} from the decision API") from None
            except OSError as exc:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise JevError(f"transport failure: {type(exc).__name__}") from None
        raise JevError("exhausted retries")

    def noul(self, state: str, instructions: str) -> tuple[float, dict]:
        """A calibrated yes/no as a probability, plus the call's metadata."""
        payload = self.ask(state, {"q": {"type": "noul", "instructions": instructions}})
        answer = payload["answers"]["q"]
        if answer.get("type") != "noul":
            raise JevError(f"expected a noul answer, got {answer.get('type')!r}")
        meta = {
            "latency_ms": payload["_latency_ms"],
            "model": payload.get("model"),
            "input_tokens": payload.get("usage", {}).get("input_tokens"),
            "cost_usd": payload.get("usage", {}).get("cost_usd"),
        }
        return float(answer["noul"]), meta
