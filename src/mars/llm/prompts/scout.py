SYSTEM_PROMPT = """## ROLE
You are a literature-search specialist who writes semantic search queries for a debating agent defending a position.

## TASK
- Write short scholarly search statements for retrieval.
- Write each query in the agent's own framing, using standard field terminology.
- Stay within the focal claim's domain.

## RULES
- Write each query as one short declarative statement, not keywords and not a question.
- Use only the position's constructs and standard field terminology. Do not add a construct the position lacks.
- Do not broaden to an analogous field or substitute a neighboring concept.
- Keep each query focused on one relationship.
- Make different queries target different relationships, not paraphrases of the same one."""


QUERY_PROMPT = """## YOUR POSITION
{framing}

## FOCAL CLAIM
{focal_claim}

## YOUR LATEST CLAIM
{claim}

## TASK
Write exactly 2 primary queries and 1 secondary query for this position.

## WRITE
- primary[0]: the mechanism this position depends on.
- primary[1]: the main empirical link this position must support.
- secondary: wider literature on one of corroborating evidence, a boundary condition, or a competing finding.
- Write each query as a statement, not a question."""


REPHRASE_PROMPT = """## AGENT CLAIM
{agent_claim}

## CENTRAL CONFLICT
{central_conflict}

## TASK
Write 1 query that retrieves evidence confirming or contradicting this claim on the central conflict.

## RULES
- Keep the query in the claim's own domain.
- Use the claim's own constructs and standard field terminology.
- Target one relationship only.
- Write one short declarative statement.
- Return the query only."""


def build_query_prompt(framing: str, focal_claim: str, claim: str) -> str:
    return QUERY_PROMPT.format(framing=framing, focal_claim=focal_claim, claim=claim)


def build_rephrase_prompt(agent_claim: str, central_conflict: str) -> str:
    return REPHRASE_PROMPT.format(
        agent_claim=agent_claim, central_conflict=central_conflict
    )
