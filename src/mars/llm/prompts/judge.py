SYSTEM_PROMPT = """## ROLE
You are a neutral adjudicator of a structured scientific debate. You do not advocate for any position.

## CONSTRAINTS
- Read the full input before writing.
- Use only the claims, evidence, mechanisms, findings, and terminology that appear in the input.
- Write for a researcher in a nearby field who knows scientific methods but not this subfield's shorthand. Use technical terms when needed, but pair abstract constructs with what they do or how researchers would observe them. Prefer concrete actor-action sentences.
- Copy corpus_ids verbatim into grounding or evidence fields only; never invent one.
- When uncertain, prefer disagreement over agreement and question over assumption."""


ASSESSMENT_PROMPT = """## AGENTS
{agents}

## FOCAL CLAIM
{focal_claim}

## PROPOSALS
{turns}

## TASK
Extract each agent's stance and the points of disagreement that set up the rebuttal round. Do not name a winner or resolve any disagreement.

## WRITE
- overview: a short neutral statement of where the debate stands after the proposals.
- stances: one explicit position per agent.
- points_of_agreement: only propositions explicitly shared by two or more agents.
- points_of_disagreement: each disagreement names the agents and the precise disputed point.
- central_conflict: the one unresolved disagreement most central to the focal claim, stated on both sides as two conflicting positions.
- critiques: who should challenge whom, on what.
- open_questions: open questions raised in the proposals.
- disagreement_present: true if the proposals contest a genuine axis (mechanism, priority, or sufficiency) even when they share the focal claim's direction; false only if the proposals are redundant with no axis to contest."""


ADJUDICATION_PROMPT = """## INITIAL RESEARCH QUERY
{research_query}

## FOCAL CLAIM
{focal_claim}

## CENTRAL CONFLICT
{central_conflict}

## TRANSCRIPT
{turns}

## CROSS-EXAMINATION EVIDENCE
Cross-examination passages come from each agent's cited papers. An agent with no passages is weakly supported, not neutral. An agent whose passages study a different domain, population, task, or system than the focal claim is supported only by analogy, not directly. Each agent's evidence relation (direct / analogical / mixed / ungrounded) is shown with its passages; verify it against the passages.
{cross_examination}

## COUNTERCLAIMS
Each is a weakness against one agent's position, with a status.
- grounded: a passage supports it.
- predictive: it follows from the claim's own logic.
{counterclaims}

## TASK
Extract what the debate resolved and what remains unresolved about the central conflict.

## REASONING ORDER
1. List what the agents agree on.
2. List what the cross-examination passages directly support: an established phenomenon (the pattern is observed) or a supported mechanism (evidence backs a cause).
3. Mark positions resting only on analogical or ungrounded evidence — they can motivate a question but cannot settle one.
4. Name the relation still contested: "which account is primary" stays unresolved even when every agent named the phenomenon.
5. State the test that would decide each contested relation.

## WRITE
- reasoning: 4 to 6 sentences on how the debate changed the central conflict.
- resolved: 2 to 4 points the debate settled, each backed by direct evidence, with the condition where it holds. Do not list a claim any unresolved question still contests.
- unresolved: 2 to 4 open questions, each a specific testable relation (which mechanism drives which outcome under which condition), not a broad theme, and the evidence that would decide it."""


HYPOTHESIS_PROMPT = """## FOCAL CLAIM
{focal_claim}

## TRANSCRIPT
{turns}

## ADJUDICATION
{adjudication}

## TASK
Extract distinct, testable hypotheses that follow from the debate and address the focal claim. Write a hypothesis only when at least one corpus_id in the transcript supports its mechanism or outcome. Do not write overlapping paraphrases of the same hypothesis. Generalize each claim to the level of the focal claim, away from any single paper or agent: keep the mechanism, outcome, and context; drop a paper's setup, benchmark, or an agent's framing. Do not write a hypothesis too narrow to address the focal claim.
- State the mechanism at the construct level. Replace paper-, dataset-, benchmark-, or example-specific details with the broader construct named in the focal claim. Do not add constructs the focal claim, transcript, adjudication, or evidence does not support.
- If the focal claim asks about stages, conditions, thresholds, validity boundaries, "under what conditions," or an explicit partition such as "which X transfer and which do not", prefer a hypothesis with a scope partition: where the claim holds, where it fails, and what boundary separates the two.
- Do not broaden the hypothesis by inventing scope cases, boundaries, remedies, or interventions. Each scope case must be supported by the transcript, adjudication, or cited evidence.

When the adjudication's unresolved question is how two accounts compare, write a comparative hypothesis that states which account is primary, which is conditional, which holds earlier, or which holds more broadly. Do not force a comparison the transcript or adjudication does not support.

## REASONING ORDER
For each hypothesis, work these steps in order, then write the fields:
1. Classify the claim_type the research problem needs: a problem about bias correction needs a comparative or causal claim about reduction, not a descriptive measurement claim.
2. State the proposition in that logical form.
3. Build the causal_chain (or explanatory pathway) from exposure to outcome.
4. Specify the study design that would test the proposition.
5. Write the warrant: why the causal_chain and evidence support the proposition; when the adjudication names a competing account, why this pathway beats or refines it.
6. Write the falsifier: the observed result that would negate it.
7. Attach the grounding corpus_ids.

## WRITE
For each hypothesis:
- claim_type: descriptive, comparative, associative, causal, or predictive. The proposition's main verb must match the claim_type. Use comparative only when the proposition itself names both compared conditions.
- proposition: one plain, testable sentence in the claim_type's logical form. Name the measured outcome and predicted direction when the claim involves change, difference, association, causation, or prediction. Comparative propositions must name both compared conditions.
- If the focal claim asks about stages, conditions, thresholds, validity boundaries, "under what conditions," or an explicit partition such as "which X transfer and which do not", the proposition may use a scope partition: it should name the valid case, the invalid case, and the boundary between them.
- A scope-partition proposition may exceed 25 words. Each clause must add one grounded scope case, boundary, or intervention/moderator.
- If the adjudication or evidence names an intervention, remedy, or moderator, the proposition may include it as a condition, such as "unless coupled to X" or "under design Y." Do not invent an intervention to broaden the hypothesis.
- Keep the proposition as broad as the focal claim. When a finding comes from one narrow setting, such as a single industry, application, or dataset, name that setting in study_design.context and leave it out of the proposition, unless the focal claim is itself about only that setting.
- causal_chain: the mechanism or explanatory pathway as a compact sequence (A -> B -> C) naming the mediator or process. For a non-causal claim_type (associative, comparative, predictive), state that logic without claiming causation.
- study_design.context: the setting, population, task, or domain.
- study_design.exposure: the main condition, intervention, or observed factor.
- study_design.comparator: the baseline or rival condition the exposure is compared against.
- study_design.outcome: the construct being evaluated; may be abstract when the measure makes it observable.
- study_design.measure: the observable metric that tests the outcome.
- warrant: why the causal_chain and evidence support the proposition; do not restate the proposition or causal_chain. When the adjudication names a competing account, explain why this pathway beats or refines that account.
- falsifier: one observed result, stated against the measure, that would negate the proposition.
- grounding: corpus_ids supporting the mechanism, outcome, or pattern, at least one.
- contributing_agents: the agents whose arguments the hypothesis draws on.

## CLAIM STRENGTH
- Match the proposition's strength to the evidence; avoid absolutes (always, never, all, every, everyone). Use resolved wording only when the adjudication resolves the relation; otherwise hedge (may, is predicted to, is associated with, should).
- The measure must be independent of the exposure. Do not test an intervention with a metric defined by the intervention's own design goal, label, or construction criteria. Prefer held-out ground truth, blinded ratings, behavioral outcomes, or an external benchmark.
- Use "necessary" only when the design removes or blocks the condition and tests whether the outcome fails. Use "sufficient" only when the condition alone produces the outcome. Do not write "more necessary." Use "primary" or "takes precedence" only when the design compares both accounts on the same measure; otherwise write a plain comparative such as "X reduces Y more than Z."
- Use precise verbs that match claim_type (detect, quantify, distinguish; reduce, attenuate; outperform, explain more variance than; predict, forecast; cause, mediate, moderate); avoid vague verbs (address, capture, handle, improve, affect)."""


SELECT_PROMPT = """## PROBLEM
{research_query}

## CENTRAL CONFLICT
{central_conflict}

## UNRESOLVED
{unresolved}

## CANDIDATE HYPOTHESES
{candidates}

## TASK
Choose the one hypothesis that best addresses the central unresolved question. Use novelty and feasibility as tie-breakers, not as substitutes for relevance.

When the central conflict is between two competing accounts, prefer the candidate that tests that comparison directly over one that restates a single agent's position, provided the comparison is testable from the candidate's proposition and grounding. If the central conflict explicitly contrasts two competing accounts, prefer a candidate whose proposition names both accounts or states their comparison directly. Do not prefer a comparative candidate on naming both accounts alone: its comparator, measure, warrant, and falsifier must be at least as strong as the best single-mechanism candidate.

Apply this viability check before novelty and feasibility. The chosen candidate must:
1. answer the central unresolved question,
2. name both competing accounts when the central conflict is between competing accounts,
3. specify an observable measure independent of the exposure,
4. specify a comparator,
5. not claim a relation resolved that the adjudication left unresolved,
6. have a claim_type that matches what the research problem needs.
Reject any candidate that uses a measure defined by the exposure's own label, goal, or construction criteria; that uses "necessary", "sufficient", "primary", or "takes precedence" without a design that can establish that claim; or that uses the phrase "more necessary".

After the viability check, apply scope coverage:
- Prefer the candidate that covers more of the central unresolved question.
- Prefer a candidate with a grounded scope partition over a single-condition hypothesis when the research problem asks about stages, conditions, thresholds, validity boundaries, "under what conditions," or an explicit partition such as "which X transfer and which do not".
- A grounded scope partition must name at least two of the following: where the claim holds, where it fails, or the boundary between them.
- Scope coverage never overrides viability. Do not select a broader candidate if it has a circular measure, missing comparator, weak falsifier, ungrounded scope case, invented intervention, or modal claim the design cannot establish.
- A scope-covering candidate must keep the focal phenomenon the research question names and tie it to an observable measure. Do not prefer a broader candidate that replaces the focal phenomenon with a generic abstraction.

## WRITE
- candidate_id: the id of the winning hypothesis (e.g. H2).
- reason: one sentence on why the winner best addresses the unresolved question, naming the competing accounts when the central conflict is between them."""


SYNTHESIS_PROMPT = """## FOCAL CLAIM
{focal_claim}

## RESEARCH PROBLEM
{problem}

## CENTRAL CONFLICT
{central_conflict}

## CANDIDATE HYPOTHESES
{candidates}

## EVIDENCE
{evidence}

## RESOLVED
{resolved}

## UNRESOLVED
{unresolved}

## SELECTED CANDIDATE
{best}

## TASK
Write a four-part research artifact for a researcher in this field. Write only about the subject matter, not the debate, the agents, or who argued what.

Write in clear, evidence-calibrated scientific prose: readable without becoming casual, precise without becoming mechanical.

Build the artifact from the selected candidate's claim_type, causal_chain, comparator, context, and measure, keeping them intact.

If the central conflict is between two competing accounts, preserve it as a comparative hypothesis rather than reducing it to a single account.

Polish and align the prose to the focal claim: replace vague verbs, soften overstrong causal language, and correct a claim_type that does not match the problem. Do not invent a missing comparator or measure or otherwise rescue an under-specified candidate.

Before writing the hypothesis, lock the scientific content: focal phenomenon, measured outcome, comparison, predicted direction, and any grounded boundary, intervention, or moderator. Preserve that content, but do not preserve abstract wording from the selected candidate when a clearer phrase says the same thing.

## WRITE
- problem: 1 to 2 sentences naming the setting, the unresolved difficulty, and why it matters.
- previous_work: 4 to 6 sentences grouping prior findings into lines of work, ending with what is resolved versus unresolved.
- reasoning: start with the general mechanism that explains the selected candidate. State it at the construct level, without naming a specific paper, dataset, benchmark, or example. Then explain how that mechanism produces the selected prediction. If a competing account is central, name it and explain whether the selected mechanism limits, refines, outperforms, or depends on it.
- hypothesis: write one or two testable sentences for a researcher in a nearby field. Use one sentence for simple claims. Use two short sentences when the hypothesis includes both a comparison and a boundary.

  First preserve the scientific content:
  - the focal phenomenon from the research question;
  - the measured outcome;
  - the comparison;
  - the predicted direction;
  - any grounded boundary, intervention, or moderator.

  Then write it naturally:
  - preserve the focal term the research question uses, such as safety theater, validity, leakage, oversight, trust decay, or factual inconsistency;
  - translate surrounding abstract phrases into what actors do, what changes, or what researchers measure;
  - hedge unless the evidence establishes the relation;
  - avoid absolutes.

  If the research problem explicitly asks for stages, conditions, thresholds, validity boundaries, "under what conditions," or an explicit partition such as "which X transfer and which do not," use a scope partition. Name at least two of the following: where the claim holds, where it fails, or the boundary between them.

  Use this form when it fits: "<focal phenomenon> holds when <observable condition>, but breaks when <observable condition>; the boundary is <measured threshold or condition>."

  If the evidence names an intervention, remedy, or moderator, include it as an explicit condition. Do not invent one.

  If the central conflict compares two accounts, name how the accounts relate: primacy, boundary, threshold, interaction, sequencing, or scope difference.

  Keep the hypothesis as broad as the focal claim. Do not carry a narrow setting, industry, dataset, benchmark, or application into the hypothesis unless the focal claim itself is limited to that setting. Put narrow settings in the study design, not the claim.

  Do not invent a boundary, intervention, remedy, comparator, or measure. Do not add clauses that merely restate the warrant."""
