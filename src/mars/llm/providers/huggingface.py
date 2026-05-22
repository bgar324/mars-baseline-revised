import asyncio
from collections import OrderedDict

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

MAX_LENGTH = 512


class HuggingFaceProvider:
    """Local HuggingFace transformer model for embedding text.

    NOTE: For SPECTER2 base, outputs are within the vector space as S2's
    specter_v2 field.
    """

    def __init__(self, model_name: str, cache_size: int = 128) -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModel.from_pretrained(model_name)
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
