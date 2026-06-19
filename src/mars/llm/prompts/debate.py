CONTEXT = """# FOCAL CLAIM

{focal_claim}

# YOUR EVIDENCE

{evidence}

# OTHER AGENTS

{agents}"""


ASSESSMENT = """# JUDGE ASSESSMENT

After the opening statements the judge mapped the debate. Engage the one central conflict below; do not relitigate ground already agreed.

Central conflict: {central_conflict}

Live disagreements:
{disagreements}

Engagement directives (who presses whom, on what):
{critiques}"""


PROPOSAL_PROMPT = """# TASK

Open the debate. Make your single strongest, evidence-grounded argument for your position on the focal claim. Lead with your one mechanism and ground it in a specific finding from your evidence.

Write the fields:
- claim: your position, as one contestable sentence.
- rationale: the mechanism and the specific finding that grounds it.
- evidence: only the paper_ids this argument uses, copied verbatim.
- message: two sentences, one idea each. Sentence 1 states your position; sentence 2 gives one evidence-grounded reason.
- action: leave null — a proposal takes no stance toward another agent.
- target_id: leave null.

Keep the message under ~35 words. Do not compare to other agents, restate the focal claim, or quote paper titles."""


REBUTTAL_PROMPT = """# TASK

First weigh the opponent's cited evidence on the central conflict: does it support, refute, clarify, or stay irrelevant to your position? Then rebut on the central conflict only, pressing the directive aimed at you. Respond to one claim, not the whole turn.

Write the fields:
- claim: the position you assert in response, as one contestable sentence.
- rationale: why you challenge or support that claim, and how the opponent's evidence weighs.
- evidence: only the paper_ids this rebuttal uses, copied verbatim.
- action: your single stance toward that claim — challenge (object), support (reinforce), or concede (it weakens part of your position).
- target_id: the one agent you are responding to.
- message: name that agent and say what you challenge or support, and why. One point only.

Use concede only when the point genuinely weakens your position. Commit to one action; do not hedge. Keep the message under ~40 words."""


REFINEMENT_PROMPT = """# TASK

Revise your position in light of the exchange, in exactly four sentences:
- S1: restate your core mechanism, sharpened by the strongest challenge it survived.
- S2: concede at most one specific sub-claim, or state plainly that no challenge defeated your position.
- S3: name the agent you most disagree with, as a fork: if X holds, your view predicts A, theirs predicts B.
- S4: name the deeper capacity or property the disagreement turns on — the underlying thing that, if present or absent, would explain why your mechanism wins where theirs fails. State it as a property of the system or task, not as "my part matters more". Name only a capacity the evidence or the exchange actually points to; if none does, say plainly that the disagreement is a genuine locus contest with no deeper mechanism identified.

Write the fields:
- claim: your sharpened position, as one contestable sentence.
- rationale: the challenge it survived and why your mechanism holds.
- evidence: only the paper_ids this turn uses, copied verbatim.
- action: your stance toward the agent in S3 — challenge, support, or concede.
- target_id: the agent you fork against in S3.
- message: the four sentences above, under ~60 words.

Do not adopt a rival's framing and do not merge your mechanism with another's ("X combined with Y", "both A and B are needed"). Hold your mechanism distinct. This is the most important rule for this turn."""


NO_EVIDENCE = """# NO EVIDENCE RETRIEVED

No passages were retrieved for this claim. Do not invent citations or corpus_ids — leave the evidence
field empty. State your position as reasoning from your perspective, and say plainly that direct
evidence was not found. An honest, ungrounded turn is a legitimate move; a fabricated citation is not."""


def render_context(focal_claim, evidence, agents):
    return CONTEXT.format(focal_claim=focal_claim, evidence=evidence, agents=agents)


def build_debate_prompt(
    phase, focal_claim, evidence, agents, prior_turns, assessment=None,
    evidence_present=True, include_context=True,
):
    parts = []
    if include_context:
        parts += [render_context(focal_claim, evidence, agents), ""]
    if not evidence_present:
        parts += [NO_EVIDENCE, ""]
    parts += [
        "# PRIOR TURNS",
        "",
        prior_turns or "(no prior turns — you open the debate)",
    ]
    if assessment is not None:
        parts += ["", assessment]
    task = {
        "proposal": PROPOSAL_PROMPT,
        "rebuttal": REBUTTAL_PROMPT,
        "refutation": REFINEMENT_PROMPT,
    }[phase]
    parts += ["", task, "", "# OUTPUT", "",
              "Based on the context and prior turns above, return only the JSON for this one turn, "
              "matching the schema. Do not exceed the word limit. No preamble or commentary."]
    return "\n".join(parts)
