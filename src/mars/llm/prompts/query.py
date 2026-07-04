SYSTEM_PROMPT = """## ROLE
You are a literature-search strategist who broadens a research query's constructs for retrieval.

## TASK
- State the scholarly domain: use the provided domain, or infer the most likely field from the constructs.
- For each construct, write 5 to 8 related terms at the same level of specificity.
- Use academic synonyms, standard technical terms, or alternative phrasings authors use for the same idea.
- Use terminology standard in the stated domain.

## RULES
- Expand each construct separately.
- Keep each expansion semantically close to the construct.
- Do not add mechanisms, outcomes, populations, assays, or examples unless the construct itself names them.
- Do not broaden to a parent category or narrow to a subtype unless authors commonly use that term for the same idea."""


EXPANSION_PROMPT = """## EXAMPLES
Construct: chronic stress
Domain: psychoneuroimmunology
Expansions: chronic stress exposure; prolonged stress exposure; sustained stress; persistent stress exposure; long-term stress exposure; repeated stress exposure

Construct: gut microbiome signatures
Domain: unspecified
Expansions: gut microbiota signatures; gut microbial signatures; intestinal microbiome signatures; fecal microbiome signatures; gut microbial profiles; gut microbiome patterns

## INPUT
Domain: {domain}
Constructs:
{constructs}

## TASK
State the domain and expand each construct.

## WRITE
- domain: the scholarly domain.
- domain_inferred: true if you inferred the domain, false if it was provided.
- expansions: one entry per construct with construct_id, construct_text, and 5 to 8 expansions."""


def build_expansion_prompt(
    constructs: list[tuple[str, str]], domain: str | None
) -> str:
    construct_lines = "\n".join(f"- {text} (id: {cid})" for cid, text in constructs)
    return EXPANSION_PROMPT.format(
        domain=domain or "unspecified",
        constructs=construct_lines,
    )


CLAIM_PROMPT = """Rewrite the research query as one neutral, testable proposition: the single claim the debate will weigh.

Rules:
- Write the proposition in the form "whether <proposition>".
- Preserve the query's relation type, such as association, effect, difference, transfer, or necessity.
- State one relationship only, unless the query is explicitly about whether two constructs are separable, transferable, or coupled; then preserve that two-part distinction. Otherwise, if the query asks several things, select the one relationship it is built around and do not join two relationships with "and".
- Keep the query's full scope. If the query asks for a distinction or taxonomy, preserve both sides of the distinction.
- Use the query's key constructs. Add no construct the query lacks.
- Leave the answer open. Do not imply a direction unless the query states it.
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
