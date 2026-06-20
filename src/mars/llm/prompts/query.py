SYSTEM_INSTRUCTION = """Given a research query's constructs, do two things:

1. State the scholarly domain. Use the provided domain; if none is provided, infer the most likely field from the constructs.
2. For each construct, write 5 to 8 related terms that broaden the literature search: academic synonyms, standard technical terms, or alternative phrasings authors use for the same idea.

Write each term at the same level of specificity as the construct. Use terminology from the stated domain."""


EXPANSION_PROMPT = """State the scholarly domain and write 5 to 8 related terms for each construct.

EXAMPLES

Construct: chronic stress
Domain: psychoneuroimmunology
Expansions: psychological stress; prolonged stress exposure; persistent stressor; HPA axis activation; allostatic load; cortisol elevation; long-term stress

Construct: gut microbiome signatures
Domain: unspecified
Expansions: gut microbiota composition; intestinal microbial profile; fecal microbiome; bacterial diversity; microbiome biomarkers; 16S rRNA signatures; gut bacterial taxa

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
Rewrite the research query as one neutral, testable proposition: the single claim the debate will weigh.

Rules:
- Write the proposition in the form "whether <X relates to Y>". State the relationship to test. Do not state the answer.
- State one relationship only. If the query asks several things, select the one relationship the query is built around. Do not join two relationships with "and".
- Keep the query's full scope. If the query asks for a distinction or taxonomy ("which X transfer and which must be redesigned"), write both sides ("which elements of X transfer and which require redesign"). Do not reduce it to one side.
- Use the query's key constructs. Add no construct the query lacks.
- Leave the answer open. Do not write "may", "might", or "could".
- Return the proposition only. Add no commentary.

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
    spans = "\n".join(lines) if lines else "(none)"
    return CLAIM_PROMPT.format(query=query, spans=spans)
