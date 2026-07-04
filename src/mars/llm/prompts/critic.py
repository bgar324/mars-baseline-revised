SYSTEM_PROMPT = """## ROLE
You are a research methodologist who identifies measurable ways a scientific claim could fail.

## CONSTRAINTS
- Work only from the claim's own constructs and standard field terminology.
- State each weakness as something a study could measure, not as a definition.
- Do not add constructs, mechanisms, or outcomes not already implied by the claim."""


DECOMPOSE_PROMPT = """## CLAIM
{claim}

## CENTRAL CONFLICT
{central_conflict}

## TASK
Break the claim down and identify the most testable way it could fail, focusing on the central conflict.

## WRITE
- proposition: the claim in plain language.
- causal_chain: how the claim says one factor produces or prevents the outcome.
- assumption: the one condition whose failure would break the causal chain and matter most for the central conflict.
- weakness: the measurable outcome that would show the assumption failing.
- counterclaim: the opposing claim that follows if the weakness holds.
- counter_queries: 2 to 3 short search queries that look for evidence of the weakness."""


CLASSIFY_PROMPT = """## PROPOSITION
{proposition}

## CAUSAL CHAIN
{causal_chain}

## ASSUMPTION
{assumption}

## WEAKNESS
{weakness}

## PASSAGES
{passages}

## TASK
Decide whether the passages support the weakness, using only the passages above.

## WRITE
- status: grounded if one or more passages support the weakness; predictive if no passage supports it but it follows from the causal_chain and assumption; rejected otherwise.
- scope: the condition under which the weakness holds. Set only when status is grounded.
- grounding: corpus_ids of the supporting passages, copied verbatim. Set only when status is grounded."""


def build_decompose_prompt(claim: str, central_conflict: str) -> str:
    return DECOMPOSE_PROMPT.format(claim=claim, central_conflict=central_conflict)


def build_classify_prompt(
    proposition: str, causal_chain: str, assumption: str, weakness: str, passages: str
) -> str:
    return CLASSIFY_PROMPT.format(
        proposition=proposition,
        causal_chain=causal_chain,
        assumption=assumption,
        weakness=weakness,
        passages=passages,
    )
