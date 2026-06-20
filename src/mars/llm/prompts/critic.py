DECOMPOSE_SYSTEM = """Decompose a debating agent's claim to locate where it could fail, then write queries to look for that failure in the literature.

# WRITE

- mechanism: the causal process by which the claim says one factor produces or prevents an outcome.
- assumption: the one condition whose failure would break the mechanism.
- weakness: the outcome a study could measure that would show the assumption failing.
- counterclaim: the opposing claim that follows from the weakness, in the form "X produces or prevents Y only if [assumption]; otherwise [outcome]".
- counter_queries: 2 to 3 queries that look for the weakness. Each states the mechanism and one failure mode as one descriptive sentence for semantic snippet search.

# CONSTRAINTS

- Use the claim's constructs and standard field terminology; add none it lacks.
- State the weakness as something a study could observe, not as a definition."""


DECOMPOSE_PROMPT = """# CLAIM
{claim}

# CENTRAL CONFLICT
{central_conflict}

# TASK
Decompose the claim and write the counter-queries."""


CLASSIFY_SYSTEM = """Decide whether the retrieved passages support a claim's weakness. Use only the passages provided; add no outside evidence.

# DECIDE status

A passage attests the weakness only if it reports the failure occurring, not if it only names the topic. Then assign one status:
- grounded: at least one passage attests the weakness.
- predictive: no passage attests the weakness, but the weakness follows from the mechanism and assumption.
- rejected: no passage attests the weakness and it does not follow from the mechanism and assumption.

# WRITE

- status: one of grounded, predictive, rejected.
- scope: required when grounded; the condition under which the weakness holds.
- grounding: required when grounded; the corpus_ids of the attesting passages, copied verbatim. Empty otherwise.

# FINAL CHECK

- grounding is non-empty only when status is grounded.
- Every corpus_id in grounding comes from a passage above."""


CLASSIFY_PROMPT = """# CLAIM
{claim}

# MECHANISM
{mechanism}

# ASSUMPTION
{assumption}

# WEAKNESS
{weakness}

# PASSAGES
{passages}

# TASK
Classify the weakness as grounded, predictive, or rejected."""


def build_decompose_prompt(claim: str, central_conflict: str) -> str:
    return DECOMPOSE_PROMPT.format(claim=claim, central_conflict=central_conflict)


def build_classify_prompt(
    claim: str, mechanism: str, assumption: str, weakness: str, passages: str
) -> str:
    return CLASSIFY_PROMPT.format(
        claim=claim,
        mechanism=mechanism,
        assumption=assumption,
        weakness=weakness,
        passages=passages,
    )
