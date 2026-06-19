import asyncio

import langextract as lx

from mars.config.settings import LangExtractSettings
from mars.llm.prompts.langextract import EXAMPLES, PROMPT


class LangExtractProvider:
    def __init__(self, settings: LangExtractSettings) -> None:
        self._settings = settings

    async def extract(
        self,
        text: str,
        *,
        extraction_passes: int | None = None,
        max_char_buffer: int | None = None,
    ) -> lx.data.AnnotatedDocument:
        return await asyncio.to_thread(
            lx.extract,
            text_or_documents=text,
            prompt_description=PROMPT,
            examples=EXAMPLES,
            model_id=self._settings.model_id,
            api_key=self._settings.api_key.get_secret_value(),
            extraction_passes=extraction_passes or self._settings.extraction_passes,
            max_char_buffer=max_char_buffer or self._settings.max_char_buffer,
            max_workers=self._settings.max_workers,
        )
