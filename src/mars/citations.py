import re

from mars.models.debate import Cycle
from mars.models.s2 import Paper

CORPUS_ID = re.compile(r"\b\d{6,}\b")


def title_map(papers: list[Paper], cycle: Cycle | None = None) -> dict[str, str]:
    titles = {
        str(p.corpus_id): p.title for p in papers if p.corpus_id is not None and p.title
    }
    if cycle:
        for evset in (*cycle.evidence.values(), *cycle.judge_evidence.values()):
            for s in evset.snippets:
                if s.title:
                    titles.setdefault(s.corpus_id, s.title)
    return titles


def label(corpus_id: str, titles: dict[str, str]) -> str:
    title = titles.get(corpus_id)
    return f'"{title}" [{corpus_id}]' if title else corpus_id


def annotate(text: str, titles: dict[str, str]) -> str:
    return CORPUS_ID.sub(lambda m: label(m.group(), titles), text)


def grounding_titles(ids: list[str], titles: dict[str, str]) -> list[str]:
    return [label(i, titles) for i in ids]
