SYSTEM_PROMPT = """Given a research query's constructs and any asserted claim, write exactly 8 hypothetical retrieval questions on the same topic. Each question must target a different retrieval angle, not a minor rewording. Stay close to the source topic, broaden only along natural dimensions, and do not introduce unrelated constructs or merely restate the claim."""


QUESTION_PROMPT = """Write exactly 8 hypothetical retrieval questions on the same topic.

Requirements:
- Each question must target a different retrieval angle.
- Keep the topic anchored to the source constructs and claim.
- Do not write near-duplicate questions.
- Do not merely restate the focal claim.
- Do not introduce unrelated constructs or narrower subtypes unless clearly implied.
- Prefer domain wording already present in the query.
- Write concise questions that could plausibly read like a paper title or opening research question.

EXAMPLES

Domain: psychoneuroimmunology
Constructs: chronic stress, immune function, epigenetic mechanisms
Claim: chronic stress alters immune function through epigenetic mechanisms
Questions:
- DNA methylation as a mechanism linking chronic stress to immune dysregulation
- Do epigenetic changes mediate the immunosuppressive effects of psychological stress?
- Cell-type specificity of stress-induced histone modifications in immune cells
- Reversibility of stress-induced epigenetic marks after stress reduction
- Comparing acute and chronic stress effects on inflammatory gene regulation
- Dose-response relationship between cumulative stress exposure and methylation burden
- Stress-related epigenetic differences across immune cell populations
- Longitudinal evidence for stress-induced epigenetic changes in immune function

Domain: microbiome research
Constructs: gut microbiome signatures, long-COVID patients
Claim: none
Questions:
- Gut microbiota composition in post-acute COVID-19 syndrome
- Are fecal microbiome profiles altered in long-COVID patients?
- Microbiome signatures distinguishing long-COVID from recovered controls
- Microbial diversity and persistent symptoms after SARS-CoV-2 infection
- Do gut microbiome shifts precede or follow long-COVID symptom onset?
- Comparing gut microbiome signatures across long-COVID symptom subtypes
- How are gut microbiome signatures measured in long-COVID studies?
- Reproducibility of gut microbiome findings across long-COVID cohorts

NOW GENERATE

Domain: {domain}
Constructs: {constructs}
Claim: {claim}
Questions:"""


def build_question_prompt(constructs: list[str], domain: str, claim: str | None) -> str:
    return QUESTION_PROMPT.format(
        domain=domain,
        constructs=", ".join(constructs),
        claim=claim or "none",
    )
