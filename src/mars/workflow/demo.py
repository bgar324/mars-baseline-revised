from mars.models.debate import (
    Adjudication,
    AgentResponse,
    AgentTurn,
    BestCandidate,
    Cycle,
    Debate,
    DebateAssessment,
    Disagreement,
    EvidenceSet,
    EvidenceSnippet,
    Hypothesis,
    MetaReview,
    Stance,
    StudyDesign,
    Synthesis,
)
from mars.models.persona import Persona
from mars.models.s2 import Author, Paper
from mars.schemas.event import StageName
from mars.schemas.query import ExtractedQuery
from mars.workflow.base import WorkflowContext


DEMO_SETUP_STEP_DELAYS = {
    "query.extract_spans": 1.0,
    "query.synthesize_claim": 3.0,
    "query.expand_query": 2.0,
    "query.generate_questions": 2.0,
    "retrieval.build_anchors": 2.0,
    "retrieval.generate_search_variants": 5.0,
    "retrieval.retrieve_candidates": 20.0,
    "retrieval.expand_corpus": 6.0,
    "cluster.embed_papers": 1.0,
    "cluster.cluster_papers": 7.0,
    "cluster.select_perspectives": 1.0,
    "persona.synthesize_personas": 14.0,
    "persona.select_panel": 1.0,
}

DEMO_DEBATE_DELAYS = {
    "debate.prepare_evidence": 18.0,
    "debate.proposal": 11.0,
    "debate.assessment": 8.0,
    "debate.rebuttal": 11.0,
    "debate.refinement": 10.0,
    "debate.adjudication": 14.0,
    "debate.synthesis": 21.0,
    "debate.select_best": 7.0,
    "debate.compose": 14.0,
}


DEMO_PAPERS = [
    Paper(
        id="demo-1",
        corpus_id=91001,
        title="Cognitive Offloading in AI-Assisted Knowledge Work",
        abstract="AI assistance changes how people allocate evaluation and composition effort.",
        authors=[Author(name="Morgan"), Author(name="Rivera")],
        year=2024,
    ),
    Paper(
        id="demo-2",
        corpus_id=91002,
        title="Automation Bias and Scientific Judgment",
        abstract="Fluent automated recommendations can increase reliance without improving validity judgments.",
        authors=[Author(name="Patel"), Author(name="Kim")],
        year=2023,
    ),
    Paper(
        id="demo-3",
        corpus_id=91003,
        title="Human Oversight in AI-Mediated Research",
        abstract="Structured verification prompts can preserve independent review behavior.",
        authors=[Author(name="Ellis"), Author(name="Okafor")],
        year=2025,
    ),
    Paper(
        id="demo-4",
        corpus_id=91004,
        title="Writing Tools, Metacognition, and Argument Quality",
        abstract="The effect of writing assistance depends on whether users actively inspect supporting evidence.",
        authors=[Author(name="Silva"), Author(name="Novak")],
        year=2024,
    ),
]


DEMO_PERSONAS = [
    Persona(
        cluster_id=0,
        references=["demo-1"],
        methods_summary="Longitudinal studies of cognitive offloading and independent task performance.",
        evidence_relation="direct",
        name="Aster",
        role="HCI Researcher",
        perspective="Focuses on how AI interfaces change the cognitive work researchers perform themselves. Prioritizes retained skill, cognitive load, and user agency in assisted workflows.",
        framing="AI-assisted writing changes which parts of scientific evaluation researchers practice themselves.",
        background="Human-computer interaction and cognitive ergonomics",
        reasoning_style="mechanistic",
        evaluation_lens="construct_validity",
        instructions=["Trace the mechanism.", "Separate assistance from replacement.", "Name observable outcomes."],
    ),
    Persona(
        cluster_id=1,
        references=["demo-2"],
        methods_summary="Controlled experiments measuring automation bias, reliance, and error detection.",
        evidence_relation="direct",
        name="Lyra",
        role="Science Studies Researcher",
        perspective="Examines how AI changes scientific judgment and production practices. Prioritizes observable reliance, error detection, and differences between perceived and actual quality.",
        framing="Fluent AI output may weaken critical evaluation by shifting attention from evidence to presentation quality.",
        background="Science of science and judgment research",
        reasoning_style="observational",
        evaluation_lens="external_validity",
        instructions=["Look for reliance behavior.", "Question ecological validity.", "Compare novice and expert use."],
    ),
    Persona(
        cluster_id=2,
        references=["demo-3"],
        methods_summary="Intervention studies of verification workflows and human oversight practices.",
        evidence_relation="mixed",
        name="Atlas",
        role="Research Methods Specialist",
        perspective="Focuses on whether verification workflows preserve meaningful human oversight. Prioritizes controlled comparisons, reproducible measures, and safeguards that can be tested directly.",
        framing="The effect depends less on tool use itself than on whether workflows require independent verification.",
        background="Academic informatics and reproducible research",
        reasoning_style="interventional",
        evaluation_lens="replicability",
        instructions=["Propose a controlled comparison.", "Require independent checks.", "Prioritize reproducible measures."],
    ),
    Persona(
        cluster_id=3,
        references=["demo-4"],
        methods_summary="Studies of metacognitive monitoring, argument revision, and writing quality.",
        evidence_relation="direct",
        name="Mira",
        role="Cognitive Scientist",
        perspective="Studies how people monitor and retain complex reasoning skills while using assistance. Prioritizes metacognitive accuracy, delayed performance, and transfer beyond the assisted task.",
        framing="AI assistance may preserve evaluation ability when researchers must explain and revise the underlying argument.",
        background="Educational psychology and metacognition",
        reasoning_style="statistical",
        evaluation_lens="predictive_power",
        instructions=["Measure retained skill.", "Distinguish confidence from accuracy.", "Test delayed performance."],
    ),
]


def populate_setup_stage(ctx: WorkflowContext, stage: StageName) -> None:
    if stage is StageName.EXTRACT:
        ctx.extracted = ExtractedQuery(
            raw_text=ctx.raw_text,
            spans=[],
            claim="Prolonged AI-assisted writing changes researchers' independent evaluation of scientific arguments.",
        )
    elif stage is StageName.RETRIEVE:
        ctx.papers = list(DEMO_PAPERS)
    elif stage is StageName.CLUSTER:
        ctx.clusters = {
            index: [paper] for index, paper in enumerate(DEMO_PAPERS)
        }
        ctx.perspectives = list(range(len(DEMO_PERSONAS)))
    elif stage is StageName.PERSONA:
        ctx.persona_pool = [persona.model_copy(deep=True) for persona in DEMO_PERSONAS]
        ctx.personas = [persona.model_copy(deep=True) for persona in DEMO_PERSONAS]


def initialize_demo_debate(ctx: WorkflowContext) -> None:
    claim = ctx.extracted.claim if ctx.extracted else ctx.raw_text
    cycle = Cycle(
        focal_claim=claim,
        problem=ctx.raw_text,
        agent_ids=[str(persona.cluster_id) for persona in ctx.personas],
        status="running",
    )
    ctx.cycle = cycle
    ctx.debate = Debate(focal_claim=claim, agents=ctx.personas, cycle=cycle)


def _paper_for(agent_id: str) -> Paper:
    return DEMO_PAPERS[int(agent_id) % len(DEMO_PAPERS)]


def _proposal(persona: Persona) -> AgentTurn:
    paper = _paper_for(str(persona.cluster_id))
    claims = {
        0: "Independent evaluation declines when AI replaces evidence inspection rather than only reducing composition effort.",
        1: "Reliance on fluent AI prose predicts lower error detection even when researchers report high confidence.",
        2: "Mandatory evidence-verification steps preserve independent evaluation better than unrestricted AI assistance.",
        3: "Researchers retain evaluation skill when AI-supported writing requires explanation and delayed independent revision.",
    }
    rationales = {
        0: "Cognitive-offloading research suggests retained ability depends on whether the underlying evaluative operation is still practiced.",
        1: "Automation-bias findings make reliance and error detection more diagnostic than writing quality alone.",
        2: "Verification workflows provide a manipulable safeguard and a direct comparison against unrestricted assistance.",
        3: "Metacognitive explanation and delayed testing distinguish short-term performance from retained independent skill.",
    }
    claim = claims.get(persona.cluster_id, persona.framing)
    return AgentTurn(
        agent_id=str(persona.cluster_id),
        phase="proposal",
        response=AgentResponse(
            claim=claim,
            rationale=rationales.get(persona.cluster_id, persona.methods_summary),
            evidence=[str(paper.corpus_id)],
            message=claim,
        ),
    )


def populate_debate_step(ctx: WorkflowContext, step_name: str) -> None:
    cycle = ctx.cycle
    if cycle is None or ctx.debate is None:
        return
    if step_name == "debate.prepare_evidence":
        for persona in ctx.personas:
            paper = _paper_for(str(persona.cluster_id))
            cycle.evidence[str(persona.cluster_id)] = EvidenceSet(
                snippets=[
                    EvidenceSnippet(
                        corpus_id=str(paper.corpus_id),
                        title=paper.title,
                        text=paper.abstract or "",
                        tier="primary",
                    )
                ]
            )
    elif step_name == "debate.proposal":
        cycle.turns.extend(_proposal(persona) for persona in ctx.personas)
    elif step_name == "debate.assessment":
        cycle.assessment = DebateAssessment(
            overview="The perspectives disagree on whether harm follows from assistance itself or from removing verification work.",
            stances=[
                Stance(agent_id=str(persona.cluster_id), position=persona.framing)
                for persona in ctx.personas
            ],
            points_of_agreement=["Independent evaluation must be measured separately from writing quality."],
            points_of_disagreement=[
                Disagreement(
                    agents=[str(persona.cluster_id) for persona in ctx.personas[:2]],
                    point="Whether cognitive offloading or automation bias is the primary mechanism.",
                )
            ],
            central_conflict="AI assistance may erode evaluation through cognitive offloading, or only when workflow design encourages uncritical reliance.",
            open_questions=["Which workflow conditions preserve delayed independent performance?"],
        )
    elif step_name == "debate.rebuttal":
        for persona in ctx.personas:
            cycle.turns.append(
                AgentTurn(
                    agent_id=str(persona.cluster_id),
                    phase="rebuttal",
                    response=AgentResponse(
                        evidence_weight="refines",
                        claim=persona.framing,
                        rationale="The competing account identifies a boundary condition rather than fully replacing this mechanism.",
                        evidence=[str(_paper_for(str(persona.cluster_id)).corpus_id)],
                        target_id=str(ctx.personas[(ctx.personas.index(persona) + 1) % len(ctx.personas)].cluster_id),
                        message="The alternative perspective is most useful as a boundary condition on this claim.",
                    ),
                )
            )
    elif step_name == "debate.refinement":
        for persona in ctx.personas:
            cycle.turns.append(
                AgentTurn(
                    agent_id=str(persona.cluster_id),
                    phase="refinement",
                    response=AgentResponse(
                        claim=persona.framing,
                        rationale="The refined position makes verification behavior and delayed performance observable.",
                        evidence=[str(_paper_for(str(persona.cluster_id)).corpus_id)],
                        message="I would narrow the prediction to workflows where researchers stop independently checking evidence.",
                    ),
                )
            )
    elif step_name == "debate.adjudication":
        cycle.adjudication = Adjudication(
            reasoning="The available evidence supports measuring retained evaluation separately from immediate writing performance. It does not establish that all AI assistance causes skill loss. Verification requirements provide the clearest boundary condition and experimental contrast.",
            resolved=["Immediate writing quality is not a valid proxy for retained evaluation skill."],
            unresolved=["Whether verification prompts fully offset long-term cognitive offloading."],
        )
    elif step_name == "debate.synthesis":
        hypothesis = Hypothesis(
            id="H1",
            claim_type="comparative",
            proposition="Researchers using AI writing assistance with mandatory evidence verification will retain higher delayed argument-evaluation accuracy than researchers using unrestricted assistance.",
            causal_chain="verification requirement -> continued evidence inspection -> preserved evaluative practice -> higher delayed accuracy",
            study_design=StudyDesign(
                context="Researchers completing repeated scientific writing tasks",
                exposure="AI writing assistance with mandatory evidence verification",
                comparator="Unrestricted AI writing assistance",
                outcome="Retained independent argument evaluation",
                measure="Blinded accuracy on delayed flaw-detection tasks completed without AI",
            ),
            warrant="The comparison isolates workflow structure while holding access to AI assistance constant.",
            falsifier="Delayed flaw-detection accuracy is equal or lower in the verification condition.",
            grounding=["91001", "91002", "91003", "91004"],
            contributing_agents=[str(persona.cluster_id) for persona in ctx.personas[:3]],
        )
        cycle.synthesis = Synthesis(hypotheses=[hypothesis])
    elif step_name == "debate.select_best" and cycle.synthesis:
        cycle.synthesis.best = BestCandidate(
            candidate_id="H1",
            reason="It directly tests whether workflow design, rather than AI access alone, determines retained evaluation skill.",
        )
    elif step_name == "debate.compose" and cycle.synthesis:
        cycle.synthesis.meta_review = MetaReview(
            problem="AI-assisted writing can improve immediate output while potentially reducing the independent evaluation researchers practice.",
            previous_work="Prior work links AI assistance to cognitive offloading and automation bias, while verification-workflow studies suggest that structured oversight can preserve active evaluation. Immediate writing quality does not establish retained skill. The unresolved issue is whether verification requirements change delayed independent performance.",
            reasoning="Requiring researchers to inspect and justify evidence keeps the evaluative operation active even when composition is assisted. Continued evaluative practice should preserve delayed flaw-detection performance relative to unrestricted assistance.",
            hypothesis=cycle.synthesis.hypotheses[0].proposition,
            best_id="H1",
        )
