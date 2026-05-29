import asyncio
import os
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import TypeVar

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

MAX_LENGTH = 512

T = TypeVar("T")


def _load_with_retry(
    loader: Callable[[], T], *, attempts: int = 3, base_delay: float = 2.0
) -> T:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return loader()
        except Exception as exc:
            last = exc
            if i < attempts - 1:
                time.sleep(base_delay * (2**i))
    assert last is not None
    raise last


class HuggingFaceProvider:
    """Local HuggingFace transformer model for embedding text.

    NOTE: For SPECTER2 base, outputs are within the vector space as S2's
    specter_v2 field.
    """

    def __init__(
        self,
        model_name: str,
        token: str | None = None,
        cache_size: int = 128,
    ) -> None:
        self._tokenizer = _load_with_retry(
            lambda: AutoTokenizer.from_pretrained(model_name, token=token)
        )
        self._model = _load_with_retry(
            lambda: AutoModel.from_pretrained(model_name, token=token)
        )
        self._model.eval()
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._cache_size = cache_size

    async def embed(self, text: str) -> np.ndarray:
        cached = self._cache.get(text)
        if cached is not None:
            self._cache.move_to_end(text)
            return cached
        result = await asyncio.to_thread(self._embed_sync, [text])
        vec = result[0]
        self._cache[text] = vec
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return vec

    async def embed_batch(self, texts: list[str]) -> np.ndarray:
        return await asyncio.to_thread(self._embed_sync, texts)

    def _embed_sync(self, texts: list[str]) -> np.ndarray:
        inputs = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=MAX_LENGTH,
            return_token_type_ids=False,
        )
        with torch.no_grad():
            out = self._model(**inputs)
        return out.last_hidden_state[:, 0, :].numpy()
