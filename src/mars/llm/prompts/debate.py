CONTEXT = """# FOCAL CLAIM

{focal_claim}

# YOUR EVIDENCE

{evidence}

# OTHER AGENTS

{agents}"""


ASSESSMENT = """# JUDGE ASSESSMENT

The judge's summary of the opening statements. Respond only to the central conflict below; the settled points are resolved, so do not reopen them.

Central conflict:
{central_conflict}

Open disagreements:
{disagreements}

Directed responses (who addresses whom, and on what):
{critiques}"""


PROPOSAL_PROMPT = """# TASK

Open the debate. State this agent's single strongest, evidence-grounded argument for its position on the focal claim, built on one mechanism grounded in a specific finding from its evidence.

# WRITE

- claim: the position, as one contestable sentence.
- rationale: the mechanism and the specific finding that grounds it.
- evidence: only the paper_ids this argument uses, copied verbatim.
- message: two sentences, one idea each, under 35 words total. Sentence 1 states the position; sentence 2 gives one evidence-grounded reason.
- action: null.
- target_id: null.

Do not compare to other agents, restate the focal claim, or quote paper titles."""


REBUTTAL_PROMPT = """# TASK

Select exactly one opposing claim that addresses the central conflict. Respond to that claim using the directive assigned to this agent.
Assign exactly one evidence_weight label for how the opponent's cited evidence affects this agent's position. The evidence is the subject of the judgment; this agent's position is the object.

# DECIDE evidence_weight

First decide whether the opponent's evidence bears on this agent's position. It bears if it addresses the same central conflict, mechanism, outcome, population, task setting, or scope. It does not bear only if it addresses a genuinely different mechanism, outcome, population, task setting, or scope.

Then assign one label:
- strengthens: it bears on the position and supports it.
- refines: it bears on the position and adds a qualification, condition, or narrower scope without weakening the core claim.
- weakens: it bears against the position, and this agent accepts that a specific part must be revised.
- disputed: it bears against the position, but this agent rejects the opponent's interpretation, scope, relevance, or validity.
- unrelated: it addresses a genuinely different mechanism, outcome, population, task setting, or scope.

# IMPORTANT DISTINCTIONS

A rival mechanism or contrary finding on the central conflict is not unrelated: assign weakens if accepted, or disputed if contested.
Assign weakens only when this agent accepts that a specific part of its position must be revised.
Assign disputed only to contest interpretation, scope, relevance, or validity; do not assign disputed to avoid a concession.
Assign refines only when the evidence narrows or qualifies the position and leaves the core mechanism intact.

# WRITE

- evidence_weight: one of strengthens, refines, weakens, disputed, unrelated.
- claim: this agent's position after weighing the evidence, as one contestable sentence.
- rationale: what the evidence shows and how it affects this agent's position.
- evidence: only the paper_ids used in this response, copied verbatim.
- conceded_point: required only when evidence_weight is weakens; the specific part of the position that is weakened.
- preserved_point: optional; the part of the position that still stands.
- revised_position: required only when evidence_weight is weakens; the revised position in one sentence.
- target_id: the one opposing agent being answered.
- message: one response under 40 words, making exactly one point.

# MESSAGE RULES

- weakens: open with "I revise: <conceded_point> ..." then state what still holds. Do not open by attacking the opponent. Do not restate the weakened claim unchanged.
- strengthens: state how the evidence reinforces the position.
- refines: state the qualification incorporated and the core claim that remains intact.
- disputed: name what is contested - interpretation, scope, relevance, or validity.
- unrelated: name the mechanism, outcome, population, task-setting, or scope mismatch."""


REFINEMENT_PROMPT = """# TASK

This is the final turn. Weigh the strongest evidence raised against this agent's position across the debate, then state where it now stands. Assign exactly one evidence_weight label. The opponent's evidence is the subject; this agent's position is the object.

# DECIDE evidence_weight

First decide whether the strongest opposing evidence bears on this agent's position, using the same bears/does-not-bear test as the rebuttal turn. Then assign one label:
- strengthens: it bears on the position and supports it.
- refines: it bears on the position and qualifies the core mechanism without overturning it.
- weakens: it bears against the position, and this agent accepts that a specific part must be revised.
- disputed: it bears against the position, but this agent contests its interpretation, scope, relevance, or validity.
- unrelated: it addresses a genuinely different mechanism, outcome, population, task setting, or scope.

A contrary finding on the central conflict is disputed if contested, not unrelated. Assign by what the evidence does to the position, not by a wish to hold the line or to appear agreeable.

# WRITE

- evidence_weight: one of strengthens, refines, weakens, disputed, unrelated.
- claim: this agent's position as it now stands, as one contestable sentence.
- rationale: what changed, what held, and why, given the evidence.
- evidence: only the paper_ids used in this turn, copied verbatim.
- conceded_point: required only when evidence_weight is weakens; the specific part of the position that is weakened.
- preserved_point: optional; the part of the position that still stands.
- revised_position: required only when evidence_weight is weakens; the revised position in one sentence.
- target_id: the agent whose evidence most affected this agent's position.
- message: one final position under 40 words. Include one contrastive test: the observation that would confirm this position and the differing observation that would confirm the opponent's. If evidence_weight is weakens, open with "I revise: <conceded_point> ...". Do not restate a weakened claim unchanged. Do not open by attacking the opponent. Do not claim that no challenge moved the position."""


NO_EVIDENCE = """# NO EVIDENCE RETRIEVED

No passages were retrieved for this claim. Do not invent citations or corpus_ids - leave the evidence
field empty. State your position as reasoning from your perspective, and say plainly that direct
evidence was not found. An honest, ungrounded turn is a legitimate move; a fabricated citation is not."""


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
        "# PRIOR TURNS",
        "",
        prior_turns or "(no prior turns - you open the debate)",
    ]
    if assessment is not None:
        parts += ["", assessment]
    task = {
        "proposal": PROPOSAL_PROMPT,
        "rebuttal": REBUTTAL_PROMPT,
        "refutation": REFINEMENT_PROMPT,
    }[phase]
    parts += [
        "",
        task,
        "",
        "# OUTPUT",
        "",
        "Return only the JSON for this one turn, matching the schema. "
        "Do not exceed the word limit. No preamble or commentary.",
    ]
    return "\n".join(parts)
