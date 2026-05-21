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
    """Build the expansion prompt.

    constructs is a list of (construct_id, construct_text) pairs.
    domain is None when no domain span was extracted.
    """
    construct_lines = "\n".join(f"- {text} (id: {cid})" for cid, text in constructs)
    return EXPANSION_PROMPT.format(
        domain=domain or "unspecified",
        constructs=construct_lines,
    )
