SYSTEM_PROMPT = """Write literature-search queries for a debating agent defending a position. Write each query as one short declarative sentence in the agent's own terms (snippet search is semantic). Do not write keywords or questions.

- Write exactly 2 PRIMARY queries: one stating the mechanism the position rests on, one stating the link the position must support. State a different relationship in each; do not rephrase one as the other.
- Write exactly 1 SECONDARY query that retrieves wider literature: corroborating evidence, a boundary condition, or a competing finding.
- Use only the position's constructs and standard field terminology. Add no construct the position lacks. Restrict every query to the focal claim's domain; do not query an analogous field."""


QUERY_PROMPT = """# YOUR POSITION
{framing}

# FOCAL CLAIM
{focal_claim}

# YOUR LATEST CLAIM
{claim}

# TASK
Write exactly 2 PRIMARY queries and exactly 1 SECONDARY query for this position."""


REPHRASE_SYSTEM = """Write 1 literature-search query that retrieves evidence which confirms or contradicts a debating agent's claim. Write one short declarative sentence (snippet search is semantic). Do not write keywords or a question. Use only the claim's constructs and standard terminology. Add no construct the claim lacks."""


REPHRASE_PROMPT = """# AGENT POSITION
{agent_claim}

# CENTRAL CONFLICT
{central_conflict}

# TASK
Write 1 query that retrieves evidence bearing on this claim and the central conflict, within the claim's own domain. Return only the query."""


def build_query_prompt(framing: str, focal_claim: str, claim: str) -> str:
    return QUERY_PROMPT.format(framing=framing, focal_claim=focal_claim, claim=claim)


def build_rephrase_prompt(agent_claim: str, central_conflict: str) -> str:
    return REPHRASE_PROMPT.format(
        agent_claim=agent_claim, central_conflict=central_conflict
    )
