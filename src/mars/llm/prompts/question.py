SYSTEM_INSTRUCTION = """Given a research query's constructs and any asserted claim, write exactly 8 hypothetical questions that read like the title or opening sentence of a paper on the same topic. The questions serve as literature-retrieval anchors. Write each question on a different angle (mechanism, association, scope, methodology, intervention, comparison). Do not rephrase one question as another, and do not rephrase the focal claim. Use the query's constructs and claim. Use terminology from the stated domain."""


QUESTION_PROMPT = """Write exactly 8 hypothetical retrieval questions, each on a different angle.

EXAMPLES

Domain: psychoneuroimmunology
Constructs: chronic stress, immune function, epigenetic mechanisms
Claim: chronic stress alters immune function through epigenetic mechanisms
Questions:
- DNA methylation as a mechanism linking chronic stress to immune dysregulation
- Do epigenetic changes mediate the immunosuppressive effects of psychological stress?
- Cell-type specificity of stress-induced histone modifications in immune cells
- Reversibility of stress-induced epigenetic marks after behavioral interventions
- Comparing acute and chronic stress effects on inflammatory gene regulation
- Dose-response relationship between cumulative stress exposure and methylation burden
- Glucocorticoid receptor gene methylation in chronically stressed populations
- Longitudinal cohort evidence for stress-induced epigenetic changes in immune cells

Domain: microbiome research
Constructs: gut microbiome signatures, long-COVID patients
Claim: none
Questions:
- Gut microbiota composition in post-acute COVID-19 syndrome
- Are fecal microbiome profiles altered in long-COVID patients?
- 16S rRNA signatures distinguishing long-COVID from recovered controls
- Microbial diversity and persistent symptoms after SARS-CoV-2 infection
- Do gut microbiome shifts precede or follow long-COVID symptom onset?
- Probiotic intervention trials for symptom relief in long-COVID patients
- Comparing gut microbiome signatures across long-COVID symptom subtypes
- Metagenomic versus 16S methods for characterizing the long-COVID microbiome

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
