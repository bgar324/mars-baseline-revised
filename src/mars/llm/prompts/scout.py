SYSTEM_PROMPT = """You write literature-search queries for a debating agent.

The agent is defending a position in a scientific debate. Write queries that retrieve passages bearing
on that position. Snippet search is semantic, so each query is one short, descriptive sentence in the
agent's own terms — not keywords, not a question.

- The two PRIMARY queries find evidence to SHAPE the argument: the mechanism it rests on and the link
  it must support. Make them two different angles on the position, not rephrasings.
- The SECONDARY query finds evidence to AUGMENT the argument from the wider literature: corroboration,
  a boundary condition, or a competing finding the agent should be ready for.
- Keep the position's constructs; use standard terminology for the field; add no construct the
  position does not contain.
- Write every query in the focal claim's own domain. The secondary query widens coverage within that
  domain; keep it there rather than moving to an analogous field."""


QUERY_PROMPT = """# YOUR POSITION

{framing}

# FOCAL CLAIM

{focal_claim}

# YOUR LATEST CLAIM

{claim}

# TASK

Based on your position and claim above, write your search queries: two PRIMARY (to shape your argument
from your own cluster) and one SECONDARY (to augment it from the wider literature). Each one short
descriptive sentence, kept in the focal claim's own domain."""


REPHRASE_SYSTEM = """You write a single literature-search query to cross-examine a debating agent's claim.

Snippet search is semantic, so the query is one short, descriptive sentence — not keywords, not a
question. Word it to surface passages that would TEST the claim: confirm it or undercut it. Keep the
claim's constructs and standard terminology; add no construct the claim does not contain."""


REPHRASE_PROMPT = """# AGENT POSITION

{agent_claim}

# CENTRAL CONFLICT

{central_conflict}

# TASK

Based on the agent's position above, write one search query to cross-examine it: a query that retrieves
passages testing whether the literature supports or undercuts this specific claim on the central
conflict, kept in the central conflict's own domain. One short descriptive sentence. Output only the query."""


def build_query_prompt(framing: str, focal_claim: str, claim: str) -> str:
    return QUERY_PROMPT.format(framing=framing, focal_claim=focal_claim, claim=claim)


def build_rephrase_prompt(agent_claim: str, central_conflict: str) -> str:
    return REPHRASE_PROMPT.format(agent_claim=agent_claim, central_conflict=central_conflict)
