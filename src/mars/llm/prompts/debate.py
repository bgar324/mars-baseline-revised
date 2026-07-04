CONTEXT = """## FOCAL CLAIM
{focal_claim}

## YOUR EVIDENCE
{evidence}

## OTHER AGENTS
{agents}"""


ASSESSMENT = """## JUDGE ASSESSMENT
Respond only to the central conflict below. Do not reopen points already resolved.

## CENTRAL CONFLICT
{central_conflict}

## POINTS OF DISAGREEMENT
{disagreements}

## CRITIQUES
{critiques}"""


EVIDENCE_WEIGHT = """## EVIDENCE_WEIGHT
- strengthens: the evidence bears on your position and supports it.
- refines: the evidence bears on your position and adds a condition without weakening the core claim.
- weakens: the evidence bears against your position and you accept that one specific part must be revised.
- disputed: the evidence bears against your position but you dispute its interpretation, scope, relevance, or validity.
- unrelated: the evidence addresses a different mechanism, outcome, population, or scope.

## CHOOSING THE LABEL
- A rival mechanism or contrary finding on the central conflict is not unrelated: weakens if you accept it, disputed only if you genuinely contest its interpretation, scope, relevance, or validity.
- Do not assign disputed to avoid a concession.
- Choose the label by what the evidence does to your position, not by a wish to hold the line or to appear agreeable.
- If the opponent's evidence is strong and you lack grounds to refute it, concede."""


PROPOSAL_PROMPT = """## TASK
Open the debate. State your single strongest argument for your position on the focal claim. Base it on one mechanism and one specific finding from your evidence.

## WRITE
- claim: your position as one contestable sentence.
- rationale: the mechanism and the finding that support the claim.
- evidence: only the corpus_ids used, copied verbatim.
- message: exactly 2 sentences under 35 words total; sentence 1 states the position, sentence 2 gives one evidence-grounded reason.
- target_id: null."""


REBUTTAL_PROMPT = """## TASK
Answer one opposing claim on the central conflict. Choose one opposing agent and state how that agent's evidence affects your position on the central conflict.

{evidence_weight}

## WRITE
- evidence_weight: one label above.
- claim: your position after weighing the evidence, as one contestable sentence.
- rationale: what the evidence shows and how it affects your position.
- evidence: only the corpus_ids used, copied verbatim.
- conceded_point: required only when evidence_weight is weakens; the part of your position you give up.
- preserved_point: optional; the part of your position that still stands.
- revised_position: required only when evidence_weight is weakens; your revised position in one sentence.
- target_id: the one opposing agent you answer.
- message: one short reply under 40 words. When evidence_weight is weakens, begin with "I revise: <conceded_point> ..."."""


REFINEMENT_PROMPT = """## TASK
Final turn. Weigh the strongest contrary evidence on the central conflict and state your position after considering it.

{evidence_weight}

## RULE
A contrary finding on the central conflict is disputed if you contest it. Do not mark it unrelated unless it addresses a different mechanism, outcome, population, or scope. Do not claim that no challenge moved your position when relevant contrary evidence was raised; if your position held, say what held and why.

## WRITE
- evidence_weight: one label above.
- claim: your position as it now stands, as one contestable sentence.
- rationale: what changed, what held, and why.
- evidence: only the corpus_ids used, copied verbatim.
- conceded_point: required only when evidence_weight is weakens; the part of your position you give up.
- preserved_point: optional; the part of your position that still stands.
- revised_position: required only when evidence_weight is weakens; your revised position in one sentence.
- target_id: the agent whose evidence most affected your position.
- message: one final position under 40 words with a contrastive test: one observation that would support your position and one that would support the opposing position. When evidence_weight is weakens, begin with "I revise: <conceded_point> ..."."""


NO_EVIDENCE = """## NO EVIDENCE RETRIEVED
No passages were retrieved for this claim. Leave the evidence field empty. Do not invent corpus_ids. State your position from your perspective and say directly that no supporting passage was found."""


PHASE_PROMPTS = {
    "proposal": PROPOSAL_PROMPT,
    "rebuttal": REBUTTAL_PROMPT,
    "refinement": REFINEMENT_PROMPT,
}


def context_block(focal_claim, evidence, agents):
    return CONTEXT.format(focal_claim=focal_claim, evidence=evidence, agents=agents)


def build_debate_prompt(
    phase,
    focal_claim,
    evidence,
    agents,
    prior_turns,
    assessment=None,
    evidence_present=True,
    include_context=True,
):
    parts = []
    if include_context:
        parts += [context_block(focal_claim, evidence, agents), ""]
    if not evidence_present:
        parts += [NO_EVIDENCE, ""]
    parts += [
        "## PRIOR TURNS",
        "",
        prior_turns or "(no prior turns - you open the debate)",
    ]
    if assessment is not None:
        parts += ["", assessment]
    task = PHASE_PROMPTS[phase]
    if "{evidence_weight}" in task:
        task = task.format(evidence_weight=EVIDENCE_WEIGHT)
    parts += [
        "",
        task,
        "",
        "## OUTPUT",
        "",
        "Return only the JSON for this one turn, matching the schema. "
        "Do not add commentary or extra text. Do not exceed the word limit.",
    ]
    return "\n".join(parts)
