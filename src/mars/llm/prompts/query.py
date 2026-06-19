SYSTEM_INSTRUCTION = """You are a scholarly information retrieval specialist. \
Given the constructs from a research query, perform two tasks:

1. Identify the scholarly domain the query operates in. If a domain is \
provided, use it. If the domain is unspecified, infer the most likely \
scholarly field from the constructs themselves.

2. For each construct, generate 5 to 8 semantically related terms that \
broaden coverage of the academic literature search space.

Each expansion term should be one of the following:
- A synonymous expression used in academic writing for the same concept
- A standard technical term associated with the construct
- An alternative phrasing authors use to refer to the same idea

Stay within each construct's conceptual neighborhood. Preserve specificity. \
Use terminology appropriate to the domain.

Return valid JSON conforming to the response schema."""


EXPANSION_PROMPT = """Identify the scholarly domain and expand each construct \
with 5 to 8 semantically related terms.

EXAMPLES

Construct: chronic stress
Domain: psychoneuroimmunology
Expansions:
- psychological stress
- prolonged stress exposure
- persistent stressor
- HPA axis activation
- allostatic load
- cortisol elevation
- long-term stress

Construct: working memory
Domain: cognitive psychology
Expansions:
- short-term memory
- executive function
- cognitive load
- memory capacity
- active maintenance
- phonological loop
- central executive

Construct: gut microbiome signatures
Domain: unspecified
Expansions:
- gut microbiota composition
- intestinal microbial profile
- fecal microbiome
- bacterial diversity
- microbiome biomarkers
- 16S rRNA signatures
- gut bacterial taxa

NOW EXPAND

Domain: {domain}
Constructs:
{constructs}

Output:"""


def build_expansion_prompt(
    constructs: list[tuple[str, str]], domain: str | None
) -> str:
    construct_lines = "\n".join(f"- {text} (id: {cid})" for cid, text in constructs)
    return EXPANSION_PROMPT.format(
        domain=domain or "unspecified",
        constructs=construct_lines,
    )


CLAIM_PROMPT = """\
Rewrite the research query as one neutral, testable proposition — the single claim the debate will weigh.

Rules:
- Form: "whether <X relates to Y>". State the relationship to be tested; do not assert the answer.
- One central relationship only. If the query asks several things, choose the most central — do not join claims with "and".
- Preserve the question's scope. If it asks for a distinction or taxonomy ("which X transfer and which must be redesigned"), keep both sides in the proposition ("which elements of X transfer and which require redesign"); do not collapse it to a single sub-contest.
- Keep the query's key constructs; add nothing it does not contain.
- Neutral, not hedged: leave the answer open, but use no "may", "might", or "could".
- Output the proposition only, no commentary.

QUERY:
{query}

EXTRACTED SPANS:
{spans}
"""


def build_claim_prompt(
    query: str,
    *,
    domain: str | None,
    goal: str | None,
    constructs: list[str],
    claim: str | None,
) -> str:
    lines: list[str] = []
    if domain:
        lines.append(f"domain: {domain}")
    if goal:
        lines.append(f"goal: {goal}")
    if constructs:
        lines.append(f"constructs: {'; '.join(constructs)}")
    if claim:
        lines.append(f"claim: {claim}")
    rendered = "\n".join(lines) if lines else "(none)"
    return CLAIM_PROMPT.format(query=query, spans=rendered)
