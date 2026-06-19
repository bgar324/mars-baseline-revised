JUDGE_SYSTEM = """Neutral judge of a structured scientific debate.

- Advocate for no position; read the whole transcript.
- Ground every output in what the transcript actually argues — introduce no claim, evidence, framework, or acronym that did not appear in it.
- Keep a partial concession partial; report agreement only where the transcript shows it, otherwise keep opposing views distinct.
- Refer to agents by name. Put raw paper_id/turn_id/agent_id strings only where the schema asks for ids."""


SYNTHESIS_SYSTEM = """You write a standalone research artifact — problem, previous work, reasoning, and a hypothesis — for researchers in a scientific field.

You are given a set of positions, findings, and evidence about a research problem. Treat them as the field's literature. Write only about the subject matter: the approaches, the methods, the findings, and what they establish or leave open. State each approach and finding directly, in its own terms.

- Ground every statement in the material provided; introduce nothing from outside it, and name each idea in the material's own terms.
- Be concrete and operational; prefer a plain description a researcher could build or measure over an abstract or theoretical label.
- Write as a self-contained contribution to the field's literature.

Return only the JSON the schema requires."""


SELECT_SYSTEM = """You identify which candidate hypothesis sits on the crux of a research problem — the claim about the subject matter that the prior findings leave open and most need resolved.

Judge the candidates on the substance: which one most directly addresses the open question at the heart of the problem, not the safest or best-supported claim. Reason and write about the approaches, mechanisms, and findings themselves, in the field's own terms.

Return only the JSON the schema requires."""


ASSESSMENT_PROMPT = """# AGENTS

{agents}

# FOCAL CLAIM

{focal_claim}

# OPENING STATEMENTS

{turns}

# TASK

Based on the opening statements above, map the terrain for a focused, two-sided rebuttal round. This is NOT adjudication — name no winner, score nothing, resolve nothing.

- stances: each agent's staked position, one sentence each.
- points_of_agreement: propositions two or more agents share — common ground the rebuttal need not relitigate. Propositions, not shared topic.
- points_of_disagreement: the live clashes, each naming the agents and the precise point (primacy, mechanism, sufficiency, definition, or scope).
- central_conflict: the one axis most central to the focal claim and still unresolved — the keystone the rebuttal round fights over. If the focal claim is multi-part or asks for a taxonomy, the axis must span its breadth (e.g. what transfers vs. what must be redesigned), not a single slice of it.
- critiques: engagement directives (who presses whom, on what weakness) — fuel for rebuttals, not a verdict.
- open_questions: unresolved threads from the proposals only.
- disagreement_present: false only if the proposals converged on one side. If you must manufacture the central_conflict, set this false.

Based on the statements above, produce the assessment."""


ADJUDICATION_PROMPT = """# FOCAL CLAIM

{focal_claim}

# CENTRAL CONFLICT

{central_conflict}

# TRANSCRIPT

{turns}

# CROSS-EXAMINATION EVIDENCE

Passages retrieved from each agent's own cited papers, to test whether the literature bears out its
claim on the central conflict. An agent with no passages here asserted a position its cited papers do
not visibly support — weigh that as weak evidential support, not as a neutral absence.

{cross_examination}

# TASK

Based on the transcript above, adjudicate the central conflict. Do NOT rank or score hypotheses — characterize the resolved and unresolved state of the conflict.

- reasoning: your chain of thought over the transcript — how the rebuttals and refinements bore on the central conflict, step by step. Weigh each agent's claim against its cross-examination evidence above.
- resolved: what the exchange settled.
- unresolved: what remains contested. When the disagreement is which factor matters more (a locus contest, e.g. architecture vs. reasoning) but the turns point to an underlying capacity or property that would explain the difference (e.g. a missing representational mechanism), name that deeper mechanism as an unresolved point, not only the surface "which matters more".

Based on the transcript and cross-examination evidence above, produce the adjudication. Frame resolved and unresolved in the focal claim's domain; if an agent argued from an analogous domain, treat that as that agent's framing and keep it out of the resolved and unresolved points."""


HYPOTHESIS_PROMPT = """# FOCAL CLAIM

{focal_claim}

# TRANSCRIPT

{turns}

# ADJUDICATION

{adjudication}

# TASK

Based on the debate above, emit the full set of hypotheses it generated: every distinct, defensible hypothesis the exchange surfaced. When the focal claim asks for a distinction or taxonomy, also emit the hypothesis that organizes the answer along that axis (e.g. which elements transfer vs. which must be redesigned), not only the single-mechanism positions.

For each hypothesis:
- statement: ONE sentence, mechanism-first. The dependent variable answers the question at the level asked. Name constructs with terms the transcript and its evidence use; do not coin a new construct label (e.g. "narrative taxonomies") for an idea the evidence states plainly.
- relationship: positive | negative | non-linear.
- mechanism: the single causal chain from IV to DV (A changes B changes C). Conditions that must hold but are not part of the chain go in assumptions.
- variables: independent, dependent, and any moderators/mediators.
- controls: held constant to isolate the IV — each a DIFFERENT entity from the IV.
- falsifier: a concrete observed result that directly negates the statement's direction; introduce no new variable.
- scope: the population/setting sampled from.
- grounding: real corpus_ids copied verbatim from the `Evidence (corpus_ids)` lines in the transcript — never a paper title. At least one per hypothesis. Every specific number, score, or named method in the statement or mechanism (e.g. "F1 < 0.25", "78% vs 72.4%", "Weibull") must come from a grounded passage; if it is not in the evidence, state the claim qualitatively instead of inventing a figure.
- contributing_agents: the agents whose arguments fed it.

Emit one hypothesis per distinct mechanism; never conjoin mechanisms into one "A and B" bundle.

One exception: when the unresolved points describe how the positions *relate* — an ordering, threshold,
interaction, or which of two mechanisms is primary (for example "X dominates until a threshold, beyond
which Y binds", or "whether structural or informational factors are the primary bottleneck") — emit
that relationship as its own hypothesis, in addition to the single-mechanism ones. A two-mechanism
primacy contest is relational: state it as one comparative claim. But match its strength to the
adjudication. If the adjudication RESOLVED the primacy, you may state it as a finding ("A drives X more
than B"). If the adjudication left the primacy UNRESOLVED — both mechanisms established but their
relative magnitude not settled — state the comparison as a PREDICTION to be tested, not a settled fact:
use predictive, falsifiable phrasing ("A will produce greater X than B under <condition>", "A is a
primary driver, testable against B"), never the asserted "A drives X more than B" or "the primary
cause". The comparison remains the contribution; it is framed as the hypothesis's claim-to-test, not as
something the debate already proved. This is a single claim about one relationship, not a bundle, and it is
often the most important hypothesis, because it is the one the collision produced and no single agent
stated.

This exception covers relationships and two-way primacy contests. Three or more independent
alternatives with no primacy claim between them ("is it mechanism A, B, or C") are not relational:
restate the positions and stop.

Based on the debate above, produce the hypotheses. Generate every one; do not rank, score, or select."""


SELECT_PROMPT = """# CENTRAL CONFLICT
{central_conflict}

# UNRESOLVED
{unresolved}

# CANDIDATES
{candidates}

# TASK
Work through these steps, then return only the JSON.

Step 1 — Read the central conflict and the unresolved points. The crux is the open question the prior
findings leave unresolved, not the safest or best-supported claim.
Step 2 — For each candidate, ask how directly it speaks to that crux. A vivid single-mechanism claim
is often less central than the comparison those findings leave open.
Step 3 — If the crux is which of two mechanisms is primary, and a candidate states the comparison
between them, that candidate is the crux; prefer it over either mechanism alone.
Step 4 — Choose the one most central candidate, and write its id with a one-sentence reason.

Constraints:
- Choose exactly one candidate.
- State the reason as a claim about the subject matter: name the competing approaches or findings and
  the open question the candidate resolves, in the field's own terms."""


SYNTHESIS_PROMPT = """# FOCAL CLAIM
{focal_claim}

# RESEARCH PROBLEM
{problem}

# CENTRAL CONFLICT
{central_conflict}

# POSITIONS
{positions}

# EVIDENCE
{evidence}

# SETTLED
{settled}

# CONTESTED
{contested}

# SELECTED CANDIDATE
{best}

# TASK
Produce a four-step research artifact — problem, previous_work, reasoning, hypothesis — for a
researcher in this field. The SELECTED CANDIDATE fixes the mechanism and direction; keep those and
restate the hypothesis cleanly around them. Do this in three steps: DRAFT each field, REVIEW the draft
against the checklist, then RETURN the corrected JSON.

## STEP 1 — DRAFT
Write the fields in order; each builds on the last.

1. problem — Pose the central difficulty as a question. Name the familiar setting first, then the
   difficulty within it, in terms a researcher here would recognize, and why it matters if it stays open.

2. previous_work — Write a related-work synthesis. Group the prior findings into the few main lines of
   work, named by what they study (e.g. "contribution-framework approaches", "process-visualization
   approaches"). For each line, give what it establishes, the specific finding that supports it, and
   what it leaves open. Then: "while <settled point> is established, whether <contested point> remains
   unsettled."

3. reasoning — Build one causal chain from the primary condition to the outcome, spelling the key step
   out in full ("X, which means Z, so Y"). Name the competing account from CONTESTED and answer it ("it
   is not that <rival account>, because <reason>; rather <the chosen mechanism>"). If CONTESTED frames
   an ordering or threshold, state it and name the measurable quantity that marks it where the material
   gives one. End by naming the specific gap the prior lines of work leave, and let it motivate the
   hypothesis.

4. hypothesis — One grammatical sentence, one main claim, every modifier folded in, filling the gap
   from reasoning. Match the subject to the claim's level (participant, model, system, method, protocol,
   or task). Name the concrete intervention or manipulated condition and the measurable outcome; if the
   candidate names an abstract property, state how it is realized or measured. Clause shapes:
   - Dense: "<subject> will <directional change> in <outcome> relative to <comparator>, with the effect
     <boundary condition> and persisting when <critical control>, challenging <rival account>."
   - Shorter: "<subject> will <directional verb> <outcome> relative to <comparator>, especially when
     <boundary condition>."
   - Minimal: "<subject> under <condition A> will <directional effect> on <outcome> compared with
     <condition B>."

## STEP 2 — REVIEW
Check the draft against every item. Where a field fails, rewrite that field before returning.

A. Standalone artifact. Refer only to approaches, methods, and findings, and write only about the
   subject matter. Attribute each statement to the approach or finding itself ("process-visualization
   approaches show…"), naming it in the field's own terms. If any field refers to who put a position
   forward, or to the process by which positions were compared, rewrite it to state the finding
   directly.
B. Grounded. Every claim, figure, construct, and method name appears in the material above; nothing is
   imported, and each idea is named in the material's own terms with no coined label. For each
   load-bearing construct the reasoning leans on (the mechanism names, thresholds, and named effects),
   the EVIDENCE or SETTLED/CONTESTED material must actually support it; if a construct appears only as
   one position's assertion and the material does not bear it out, present it as a proposed/contested
   mechanism ("approaches that posit <X>"), not as an established finding. State qualitatively any
   effect the material gives no figure for.
C. Operational hypothesis. The hypothesis names a concrete intervention/condition and a measurable
   outcome, not only an abstract construct. Replace any named paradox or theoretical label with a plain
   description a researcher could build or measure.
D. Hypothesis form. One sentence. A control and a comparison sit in separate clauses ("persisting when
   <control> is held constant" and "<verb> more than <baseline>"), never fused as "improved than".
   While CONTESTED leaves the rival open, write "a primary cause" or "more than <named rival>", never
   "the primary cause".
E. Scope and domain. The four fields answer the full RESEARCH PROBLEM in its own domain; if it names two
   phenomena, both are covered; it is not reframed into an analogous domain.
F. Lengths. problem 1-2 sentences; previous_work 4-6; reasoning one short paragraph; hypothesis exactly
   one sentence. problem, previous_work, and reasoning are full flowing prose, not fragments.
G. Claim strength matches what was resolved. If the hypothesis asserts one mechanism matters MORE than
   another, check the adjudication: if it left that primacy unresolved, the hypothesis must PREDICT the
   direction ("will produce greater… than… under <condition>"), not ASSERT it as established ("drives…
   more than", "the primary cause"). Keep the comparison; frame it as the claim to be tested.

## STEP 3 — RETURN
Return only the corrected JSON."""
