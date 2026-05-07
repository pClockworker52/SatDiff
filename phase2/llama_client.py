"""Thin HTTP client matching the VLM interface, talking to llama-server.

Replaces the transformers-based VLM with a llama.cpp-server transport for
the GGUF Q8_0 backbone + F16 mmproj quantized from the Stage 1 fine-tune.
Same `model_id`/`load()`/`generate()` surface so phase2.runner is transport-
agnostic.

Server is assumed to be already running (started outside this process).
Default URL: http://localhost:8080. Override with LLAMA_SERVER_URL.
"""

from __future__ import annotations

import base64
import io
import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from PIL import Image


@dataclass
class LlamaServerVLM:
    """llama-server transport. Same surface as phase2.runner.VLM."""
    model_id: str = "llama-server"
    base_url: str = ""
    timeout_s: float = 120.0

    def load(self) -> "LlamaServerVLM":
        if not self.base_url:
            self.base_url = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080")
        # Sanity ping — fail loud if the server isn't reachable.
        r = requests.get(f"{self.base_url}/health", timeout=5)
        r.raise_for_status()
        return self

    def generate(self, images: list[Image.Image], prompt: str,
                 max_new_tokens: int = 1024) -> tuple[str, float]:
        content: list[dict] = []
        for im in images:
            content.append({"type": "image_url", "image_url": {"url": _to_data_uri(im)}})
        content.append({"type": "text", "text": prompt})

        body = {
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_new_tokens,
            "temperature": 0.0,
            "stream": False,
        }

        t0 = time.perf_counter()
        r = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=body, timeout=self.timeout_s,
        )
        latency = time.perf_counter() - t0
        r.raise_for_status()
        data: dict[str, Any] = r.json()
        text = data["choices"][0]["message"]["content"]
        return text, latency


def _to_data_uri(image: Image.Image) -> str:
    if image.mode != "RGB":
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
