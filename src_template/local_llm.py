"""
local_llm.py — Local GGUF-based LLM client with GPU offloading.

Drop-in API-compatible replacement for llm_client.LMClient but runs
inference locally via llama-cpp-python. Same .chat() / .try_chat() /
.available interface — speed_run.py doesn't care which backend it calls.

GPU offloading:
- macOS: Metal (mlock + n_gpu_layers=0 for auto)
- Linux/Colab: CUDA (n_gpu_layers=-1 for full offload, or specify layers)
- CPU fallback on any platform

Uses:
- pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
  (for CUDA 12.1 on Colab)
- Or just: pip install llama-cpp-python (CPU/Metal)

Model download (one-time):
- wget https://huggingface.co/bartowski/gemma-3-12b-it-GGUF/resolve/main/gemma-3-12b-it-Q4_K_M.gguf
  (~7GB, good for prose, fits in T4 16GB VRAM with context window)

Why this over API:
- Zero per-token cost
- Zero network latency
- Can run millennia at hyperspeed without rate limits
- With Colab Pro GPU (Blackwell), ~50-80 tok/s on Q4 Gemma 12B
- Yearly chronicle (800 tokens output) = ~10-15 seconds per world per year
- 200 years × 5 worlds = 1000 chronicles = ~3-4 hours on Blackwell GPU
"""

import os
import time
import json
from typing import Optional, Dict, Any, List


class LocalLLMClient:
    """Local GGUF-based LLM. Same interface as LLMClient for drop-in."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,  # -1 = all layers to GPU
        temperature: float = 0.7,
        verbose: bool = False,
    ):
        self.model_path = model_path or os.environ.get(
            "LLM_LOCAL_MODEL_PATH", ""
        )
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.default_temperature = temperature
        self.verbose = verbose
        self._model = None
        self._available = None
        self._load_error = None
        self.backend = "local"
        self._total_tokens = 0
        self._total_calls = 0

    @property
    def available(self) -> bool:
        """Check if model is loaded and ready."""
        if self._available is not None:
            return self._available

        if not self.model_path:
            self._load_error = "No model path provided"
            self._available = False
            return False

        if not os.path.exists(self.model_path):
            self._load_error = f"Model not found: {self.model_path}"
            self._available = False
            return False

        try:
            from llama_cpp import Llama

            load_kwargs = {
                "model_path": self.model_path,
                "n_ctx": self.n_ctx,
                "verbose": self.verbose,
                "n_threads": os.cpu_count() or 4,
            }

            # GPU offloading
            if self.n_gpu_layers != 0:
                load_kwargs["n_gpu_layers"] = self.n_gpu_layers

            # Metal on macOS
            if "Darwin" in os.uname().sysname:
                load_kwargs["n_gpu_layers"] = self.n_gpu_layers if self.n_gpu_layers > 0 else 0

            self._model = Llama(**load_kwargs)
            self._available = True
            self._load_error = None
            if self.verbose:
                print(f"    [LLM LOCAL] Loaded {self.model_path} with {self.n_gpu_layers} GPU layers")
            return True

        except ImportError:
            self._load_error = "llama-cpp-python not installed. Run: pip install llama-cpp-python"
            self._available = False
            return False
        except Exception as e:
            self._load_error = f"Failed to load model: {e}"
            self._available = False
            if self.verbose:
                print(f"    [LLM LOCAL] Error: {e}")
            return False

    def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 512,
        stop: Optional[list] = None,
    ) -> Optional[str]:
        """
        Generate a chat completion locally.
        Same signature as LLMClient.chat() for drop-in compatibility.
        Returns None if model not loaded or generation fails.
        """
        if not self.available or self._model is None:
            return None

        # Format messages into llama.cpp chat format
        # llama.cpp handles system/user/assistant roles
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                formatted.append({"role": "system", "content": content})
            elif role == "user":
                formatted.append({"role": "user", "content": content})
            elif role == "assistant":
                formatted.append({"role": "assistant", "content": content})

        try:
            # Use the high-level chat interface
            result = self._model.create_chat_completion(
                messages=formatted,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop or [],
                stream=False,
            )

            self._total_calls += 1

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"].get("content", "").strip()
                self._total_tokens += len(content.split())  # rough estimate
                return content
            return None

        except Exception as e:
            if self.verbose:
                print(f"    [LLM LOCAL] Generate error: {e}")
            return None

    def try_chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 512,
        max_retries: int = 2,
    ) -> Optional[str]:
        """Chat with retries. Same interface as LLMClient.try_chat()."""
        for attempt in range(max_retries + 1):
            result = self.chat(messages, temperature=temperature, max_tokens=max_tokens)
            if result:
                return result
            if attempt < max_retries:
                time.sleep(1.0 * (attempt + 1))
        return None

    def stats(self) -> Dict[str, Any]:
        """Return inference statistics."""
        return {
            "model_path": self.model_path,
            "loaded": self._available or False,
            "total_calls": self._total_calls,
            "estimated_tokens": self._total_tokens,
            "load_error": self._load_error,
        }

    def unload(self):
        """Free GPU memory by unloading the model."""
        if self._model is not None:
            del self._model
            self._model = None
            self._available = None
            self._load_error = None

    def reload(self):
        """Reload the model after unload."""
        self._available = None
        self._load_error = None
        _ = self.available  # trigger lazy load


# ═══════════════════════════════════════════════════════════════════
# BATCH CHRONICLE GENERATION
# ═══════════════════════════════════════════════════════════════════

def batch_generate_chronicles(
    client: LocalLLMClient,
    chronicle_requests: List[Dict[str, Any]],
    max_tokens: int = 800,
    temperature: float = 0.7,
) -> List[Optional[str]]:
    """
    Generate multiple chronicles sequentially (llama.cpp is CPU-bound on
    sampling, so batching doesn't help — sequential with large batch_size
    param doesn't apply here). But this wrapper handles errors gracefully
    so one failure doesn't kill the batch.

    Each request: {"world_id": str, "year": int, "messages": list}

    Returns list of prose strings (same order), None for any failures.
    """
    results = []
    for i, req in enumerate(chronicle_requests):
        result = client.chat(
            messages=req["messages"],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        results.append(result)

        # Verbose progress
        if client.verbose and (i + 1) % 10 == 0:
            print(f"    [LLM BATCH] {i+1}/{len(chronicle_requests)} chronicles generated")

    return results
