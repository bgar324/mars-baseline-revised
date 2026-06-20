JUDGE_SYSTEM = """Judge a structured scientific debate.

- Take no position.
- Read the entire transcript before writing.
- Use only claims, evidence, frameworks, and acronyms that appear in the transcript.
- When the transcript shows partial agreement, report it as partial; otherwise keep opposing views distinct.
- Name agents by name. Put raw paper_id/turn_id/agent_id strings only in schema fields that ask for ids."""


ADJUDICATION_SYSTEM = """Judge a structured scientific debate. Decide what became clearer and what remains unresolved about the focal claim.

- Take no position on any agent, view, or hypothesis.
- Use only the focal claim, central conflict, transcript, cross-examination evidence, and counterclaims provided.
- Add no outside claims, paper titles, citations, frameworks, examples, acronyms, or terminology.
- When the transcript shows a refinement, report it as a refinement; do not state full consensus.
- Use cited papers only to judge support; use agent turns only to identify claims, concessions, refinements, and disagreements.
- Write about mechanisms, findings, and open questions, not about who argued what.
- Name opposed views with short descriptive labels derived from the central conflict.
- State resolved items as what became clearer; state unresolved items as what still needs testing."""


SYNTHESIS_SYSTEM = """Write a standalone research artifact: problem, previous work, reasoning, and a hypothesis, for researchers in a scientific field.

- Treat the supplied findings and evidence as the field's literature.
- Write about the subject matter only; do not mention a debate, panel, agents, personas, or positions taken.
- Use only the material provided; add nothing from outside it.
- State each construct as something a researcher could build or measure; do not leave an abstract label alone."""


SELECT_SYSTEM = """Select which candidate hypothesis captures the central unresolved question of a research problem: the claim prior findings leave open and most need resolved.

- Judge candidates on substance, not on which is safest, broadest, or best-supported.
- Write about the approaches, mechanisms, and findings in the field's own terms."""


ASSESSMENT_PROMPT = """# AGENTS

{agents}

# FOCAL CLAIM

{focal_claim}

# OPENING STATEMENTS

{turns}

# TASK

Name the positions and clashes for a rebuttal round.

Use only the agents and opening statements above. Do not name a winner, score agents, resolve disputes, or write a final answer.

# WRITE

Return these fields:

- stances: one sentence per agent stating the position the agent commits to. State the claim, not the topic.
- points_of_agreement: propositions stated by two or more agents.
- points_of_disagreement: each entry names the agents, one disagreement type, and the exact incompatibility.
- central_conflict: one contested question with two opposed poles, spanning the focal claim's full breadth.
- critiques: each entry names who responds to whom, the relation (challenge | support | concede), and one precise point to engage.
- open_questions: questions left open by the proposals above; add no new issues.
- disagreement_present: false when the openings converge, when the only difference is stylistic or methodological wording, or when a central conflict would have to be invented; true otherwise.

# DISAGREEMENT TYPES

Classify a disagreement type by its operational condition:

- primacy: the agents claim different factors matter most.
- mechanism: the agents claim different causal paths to the same outcome.
- sufficiency: one agent claims a factor is enough; another claims it is not.
- definition: the agents assign different meanings to the same construct.
- scope: the agents claim the same effect holds in different populations or settings.
- evidence_standard: the agents require different evidence to accept the claim.

# CONSTRAINTS

- State each point as a precise proposition, not a broad theme.
- Classify two methods as disagreement only when they imply incompatible claims about primacy, sufficiency, mechanism, definition, scope, or evidence standard.
- When two agents are compatible, mark the relation support or refinement, not challenge.
- When an agent's claim fits both poles, mark it orthogonal to the central conflict; do not seat it in opposition.
- A bridge position must clarify the central conflict's axis, not introduce a third topic.
- central_conflict and critiques must match the stances in the openings."""


ADJUDICATION_PROMPT = """# INITIAL RESEARCH QUERY

{research_query}

# FOCAL CLAIM

{focal_claim}

# CENTRAL CONFLICT

{central_conflict}

# TRANSCRIPT

{turns}

# CROSS-EXAMINATION EVIDENCE

Passages retrieved from each agent's cited papers to test whether the literature supports that agent's claim on the central conflict.

When an agent has no passages, treat its claim as weakly supported. Do not treat missing passages as neutral.

{cross_examination}

# COUNTERCLAIMS

Each line is a counterclaim against one agent's position, with a status.

- grounded: a retrieved passage attests the weakness.
- predictive: no passage attests the weakness, but the weakness follows from the claim's own logic.
- rejected or None: do not use.

{counterclaims}

# TASK

Decide what became clearer and what remains unresolved about the CENTRAL CONFLICT.

Write a field-level overview. Keep the main mechanisms, conditions, and open comparisons that help answer the FOCAL CLAIM. Do not preserve every narrow paper detail, method detail, benchmark detail, or agent-specific phrasing.

Use only the material above. Add no outside claims, evidence, frameworks, examples, citations, paper titles, agent names, or new terminology.

# REASONING SEQUENCE

Work through these steps before writing the JSON.

Step 1: Identify the two views.
Restate the central conflict as two broad subject-matter views. Use terms from the CENTRAL CONFLICT, not agent names.

Step 2: Identify the final positions.
For each agent, use the final claim, revised claim, concession, and message. Do not rely on action labels alone.

Count a concession only when the agent weakens its own earlier claim and states a revised position.

Step 3: Check support.
Use cross-examination evidence to decide whether each final position is directly supported, weakly supported, mixed, or untested.

A cited paper supports a claim only when the retrieved passage directly supports that claim.

If the evidence can support more than one interpretation, or if the claim is plausible but not directly tested, keep the issue unresolved.

Step 4: Reduce the debate.
Convert agent-specific claims into field-level claims about the FOCAL CLAIM.

Keep:
- the main mechanism
- the main outcome
- the scope where the mechanism holds
- the comparison that remains unsettled

Drop:
- one paper's setup
- one benchmark detail
- one model family unless the focal claim requires it
- one metric unless the evidence only supports that metric
- one isolated method
- agent-specific wording
- side issues that do not answer the focal claim

Step 5: Decide what became clearer.
A point is resolved only when the transcript and cross-examination evidence support it and no grounded counterclaim overturns it.

Write resolved points as broad takeaways, not narrow findings.

Step 6: Decide what still needs testing.
A point is unresolved when agents still disagree, evidence is mixed, evidence is indirect, or the deciding comparison was not tested.

A predictive counterclaim becomes an unresolved issue.

Step 7: Compress.
Combine narrow points that support the same broader takeaway. Prefer one clear overview claim over several niche claims.

# WRITE

Return exactly this JSON shape:

{{"reasoning": "", "resolved": [], "unresolved": []}}

- reasoning:
  4 to 6 sentences. Name the two broad views, state what became clearer or more conditional, and explain what this means for the focal claim or initial research query.

- resolved:
  2 to 4 strings. Each string is one broad takeaway about what became clearer.
  Each item must answer the focal claim, name the mechanism, and state the scope or condition where it holds.

- unresolved:
  2 to 4 strings. Each string is one broad open question.
  Each item must name the disputed relation and the comparison or condition that would decide it.

# STYLE

Write like a concise literature-review overview.

Good resolved item:
"Provenance records clarify authorship when they document both user actions and AI contributions."

Good unresolved item:
"Whether authorship should be judged by interaction records or institutional intent standards remains unresolved."

Avoid:
"Whether the interaction between visual timeline interfaces and immutable W3C metadata logs dominates standalone qualitative provenance systems in high-stakes authorship attribution remains unresolved."

Avoid:
"X affects Y positively, strongest in Z, holding A constant."

# FINAL CHECK

Before returning, rewrite any resolved or unresolved item that:
- is mainly about one paper, benchmark, model, method, or interface
- repeats an agent's wording too closely
- contains several stacked conditions
- would not read as a high-level literature-review takeaway
- is narrower than the focal claim
- uses obscure implementation detail where a broader mechanism would suffice
- lists the same idea in both resolved and unresolved
- uses "relates to," "impacts," or "affects" without naming the mechanism

Do not write "more research is needed."
Do not write a final hypothesis.
Do not rank, score, select candidates, or name a winner.
Do not include raw paper IDs, agent names, paper titles, author-year citations, or invented citations.
Do not use "Position A," "Position B," "side one," or "side two."
Keep each resolved and unresolved string under 30 words.
Return only valid JSON."""


HYPOTHESIS_PROMPT = """# FOCAL CLAIM

{focal_claim}

# TRANSCRIPT

{turns}

# ADJUDICATION

{adjudication}

# TASK

Extract the hypotheses that follow from the debate.

Do not treat every agent claim as a hypothesis. A hypothesis should capture a claim that helps answer the focal claim after the debate has exposed what is supported, what is limited, and what remains unsettled.

Use only the transcript and adjudication. Do not rank, score, select, or mark a best hypothesis.

Admit a hypothesis only when at least one real corpus_id from an `Evidence (corpus_ids)` line in the transcript supports its core mechanism or outcome. Copy corpus_ids verbatim. Use paper IDs only, never paper titles.

# REASONING SEQUENCE

Work through these steps before writing the output.

Step 1: Find the central question.
Restate, silently, what the focal claim is really asking. Use this to ignore side claims, paper details, and agent-specific wording.

Step 2: Identify the live claims.
Keep only claims that directly answer the focal claim. Drop claims that are background, method descriptions, examples, or evidence details.

Step 3: Separate settled claims from open claims.
A settled claim is directly supported by the transcript and grounding.
An open claim is plausible but still disputed, conditional, or not directly tested.

Do not turn every open claim into a hypothesis. Keep only open claims that would make a useful research prediction.

Step 4: Compress each claim.
For each remaining claim, reduce it to:
- what changes
- what outcome changes
- why it changes
- where the claim applies

If the claim cannot be reduced this way, drop it.

Step 5: Write the statement plainly.
Write the statement as a sentence a researcher might actually use.

Do not write a sentence that sounds like a filled template.

Do not include controls, caveats, and every qualifier in the statement. Put those in their own fields.

Step 6: Check grounding.
Keep the hypothesis only if at least one real corpus_id from an `Evidence (corpus_ids)` line supports the core mechanism or outcome.

Use paper IDs only. Do not use paper titles.

# DISTINCTNESS

Emit one hypothesis only when it makes a genuinely different prediction about:
- the main mechanism
- the main outcome
- the condition where the mechanism holds
- the comparison that would decide an unresolved issue

Do not emit a separate hypothesis just because one agent cited a different paper, method, benchmark, model, or metric.

Do not force a comparative or conditional hypothesis unless the transcript or adjudication supports that relation.

# WRITE

For each hypothesis, return these fields:

- statement:
  One plain, testable sentence under 25 words.
  Say what is expected to change and in what setting.
  Name the outcome and direction.
  Include scope or condition only when needed.
  Do not include controls.

- relationship:
  positive | negative | non-linear.

- is_relational:
  true only when the statement compares, orders, conditions, or relates two mechanisms.
  false for one mechanism.
  A relational statement must make one claim about the relation. Do not bundle mechanisms.

- mechanism:
  One short causal chain under 25 words.
  Use the form: "X changes Y, which changes Z."
  Do not bundle multiple chains.
  Put background conditions in assumptions.

- variables:
  independent, dependent, and any mediators and moderators.
  Use simple construct names from the transcript or evidence.
  Do not invent new construct labels.

- controls:
  Variables held constant to isolate the independent variable.
  Each control must be distinct from the independent variable and must not be a variable the mechanism runs through or produces.
  Do not repeat controls in the statement.

- assumptions:
  Conditions required for the hypothesis to hold but not part of the causal chain.
  List only essential assumptions.

- falsifier:
  One observed result that would negate the statement's predicted direction.
  Do not introduce a new variable.

- scope:
  The population, task setting, model class, or domain where the hypothesis applies.

- grounding:
  corpus_ids copied verbatim from the transcript.
  Use paper IDs only.
  Include at least one corpus_id.

- contributing_agents:
  Agents whose arguments contributed to the hypothesis.

# WRITING STANDARD

Prefer simple research prose.

Good:
"In high-stakes writing contexts, provenance records should improve authorship attribution."

Good:
"Visual interaction histories should improve writers' ability to recognize AI influence in collaborative writing."

Good:
"Metadata logs should make authorship claims more verifiable across multi-agent writing systems."

Avoid:
"X affects Y positively, strongest in Z, holding A constant."

Avoid:
"X impacts Y through Z."

Avoid:
"X relates to Y."

Avoid:
"The integration of abstract mechanism A with abstract mechanism B affects abstract outcome C."

# CLAIM STRENGTH

Use settled wording only when the adjudication resolves the relation and the transcript contains a genuine concession supporting it.

Otherwise phrase the statement as a prediction:
- "should"
- "is expected to"
- "is predicted to"
- "may"

Use "necessary" or "sufficient" only when the evidence directly supports that logical strength.

# FINAL CHECK

Before returning, remove any hypothesis that:
- is mostly about one paper, benchmark, method, model, metric, or interface
- repeats an agent's wording
- contains more than one causal chain
- puts controls inside the statement
- uses vague verbs without direction
- introduces constructs not present in the transcript or adjudication
- is too broad for the grounding
- is too narrow to answer the focal claim
- has empty grounding

Do not rank, score, select, or mark a best hypothesis.
Do not include raw paper titles, author-year citations, or invented terminology.
Do not write a meta-review or final synthesis.
Return only the full hypothesis set as valid JSON."""


SELECT_PROMPT = """# CENTRAL CONFLICT

{central_conflict}

# UNRESOLVED POINTS

{unresolved}

# CANDIDATE HYPOTHESES

{candidates}

# TASK

Select the one hypothesis that best captures the central unresolved question of the debate: the question the adjudication left open, not the safest, broadest, or best-supported standalone claim.

# REASONING SEQUENCE

Work through these steps before writing the JSON.

Step 1: Identify the unresolved question.
Read the CENTRAL CONFLICT and UNRESOLVED POINTS. Decide what issue most needs testing.

Step 2: Filter candidates.
Keep only candidates that directly answer the central conflict or at least one unresolved point.

Step 3: Prefer the candidate that tests the unresolved relation.
When the unresolved issue asks how two mechanisms compare, prefer a candidate that states that comparison.

Do not prefer a relational candidate merely because it is relational. Prefer it only when its statement, mechanism, and grounding make the comparison testable.

Step 4: Avoid peripheral support.
Do not select a well-supported candidate if it answers a side issue rather than the central unresolved question.

Step 5: Break ties.
If candidates remain tied, select the one with the clearer falsifier and tighter variables.

# WRITE

Return exactly this JSON shape:

{{ "candidate_id": "", "reason": "" }}

- candidate_id:
  The id of the selected candidate.

- reason:
  A subject-matter claim that names the competing mechanisms, findings, or positions and states why the selected hypothesis addresses the central unresolved question better than the alternatives.

# CONSTRAINTS

- Do not select a candidate that restates one agent's opening claim unless no relational or unresolved-focused candidate is comparably testable.
- Do not select a well-supported peripheral candidate over a testable candidate that targets the unresolved relation.
- Do not write the reason as a comment about the prompt.
- Return only the JSON object."""


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

Write a four-part research artifact for a researcher in this field.

The SELECTED CANDIDATE fixes the main mechanism, direction, comparison, and scope. Preserve those elements, but rewrite them clearly and naturally.

Do not mention agents, debate turns, adjudication, selected candidates, or who argued what.

Use only the provided material.

# REASONING SEQUENCE

Work through these steps before writing the JSON.

Step 1: Name the research setting.
Identify the familiar field setting from the RESEARCH PROBLEM.

Step 2: Name the unresolved difficulty.
Explain what remains hard to determine and why it matters.

Step 3: Organize previous work.
Group the evidence into a few lines of work. For each line, state what it studies, what it establishes, and what it leaves open.

Step 4: Build one causal chain.
Explain why the selected mechanism should produce the outcome.

Use one chain:
X changes Y, which changes Z, so W.

Step 5: Answer the rival account.
Name the rival account from CONTESTED. Explain why the selected mechanism is expected to matter under the stated condition.

Step 6: Write the hypothesis.
Write one testable sentence. Keep the comparison. Include the boundary condition or control only when present in the selected candidate.

# WRITE

Return exactly this JSON shape:

{{
"problem": "...",
"previous_work": "...",
"reasoning": "...",
"hypothesis": "..."
}}

- problem:
  1 to 2 sentences. Name the familiar research setting, the unresolved difficulty within it, and why it matters.

- previous_work:
  4 to 6 sentences. Group prior findings into a few named lines of work using field-specific terms.
  For each line, state what it studies, what it establishes, and what it leaves open.
  End with: "While <settled point> is established, it remains unsettled whether <contested point>."

- reasoning:
  One short paragraph.
  Build one causal chain as "X changes Y, which means Z, so W."
  Name the rival account from CONTESTED and answer it:
  "It is not that <rival account>, because <reason>; rather, <selected mechanism>."
  When the selected candidate is comparative, state the condition under which one mechanism is predicted to matter more.
  End by naming the gap that motivates the hypothesis.

- hypothesis:
  Exactly one sentence naming the manipulated factor, measurable outcome, comparator, boundary condition or moderator when present, critical control when present, and rival account when present.

# STYLE

Prefer direct research prose.

Good:
"Combining provenance interfaces with metadata logs should improve authorship attribution in high-stakes writing contexts."

Avoid:
"The integration of qualitative provenance interfaces with immutable technical metadata affects the reliability of authorship redefinition in a positive direction."

Good:
"This should matter most when authors have incentives to misrepresent how much AI contributed."

Avoid:
"The effect is strongest in high-stakes attribution scenarios, holding the degree of AI assistance constant."

# CONSTRAINTS

- Write only about the research problem, approaches, methods, findings, and mechanisms.
- Do not mention agents, debate turns, adjudication, selected candidates, or who argued what.
- Use only constructs, method names, thresholds, numbers, and named effects that appear in the provided material.
- Import nothing from outside the provided material.
- Present a construct that appears only as a contested assertion as proposed or contested.
- State an ungrounded figure qualitatively.
- Keep each named construct's term, but state its operational realization alongside it.
- Do not let an abstract label stand alone.
- The dependent variable must be an outcome the cited evidence measures. If the evidence measures a different outcome, restate the dependent variable as the measured outcome or mark the claim predictive.
- State a comparison as "relative to <comparator>" and a control as "when <control> is held constant"; do not fuse them.
- Cover the full RESEARCH PROBLEM in its own domain.
- Keep the comparison in the hypothesis.
- Assert a primacy claim as established only when the primacy sits in SETTLED, the candidate states it as a finding, and a cited passage grounds the relation itself, not each mechanism separately. Otherwise predict the direction. When in doubt, predict.
- Return only valid JSON."""
