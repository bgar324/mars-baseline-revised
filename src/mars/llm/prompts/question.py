SYSTEM_INSTRUCTION = """You are a scholarly information retrieval specialist. \
Given the constructs and any asserted claim from a research query, write 3 to \
5 hypothetical questions that read like the title or opening sentence of a \
paper studying the same topic. These questions will be used as additional \
anchors for literature retrieval.

Each question should:
- Read like a paper title or the first sentence of an abstract
- Cover a distinct angle on the topic (mechanism, association, scope, \
methodology, intervention, comparison)
- Use terminology appropriate to the domain
- Stay grounded in the constructs and claim
- Probe related but distinct facets of the topic, not paraphrase the focal claim

Return valid JSON conforming to the response schema."""


QUESTION_PROMPT = """Generate 3 to 5 hypothetical questions for retrieval.

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

Domain: microbiome research
Constructs: gut microbiome signatures, long-COVID patients
Claim: none
Questions:
- Gut microbiota composition in post-acute COVID-19 syndrome
- Are fecal microbiome profiles altered in long-COVID patients?
- 16S rRNA signatures distinguishing long-COVID from recovered controls
- Microbial diversity and persistent symptoms after SARS-CoV-2 infection

Domain: machine learning interpretability
Constructs: attention mechanisms, transformer models, feature attribution
Claim: attention weights provide faithful explanations of model predictions
Questions:
- Do attention weights reliably explain transformer predictions?
- Attention is not Explanation: empirical analysis on classification tasks
- Comparing attention-based and gradient-based attribution methods
- Faithfulness of self-attention as a feature attribution signal
- When does attention align with model behavior in transformers?

NOW GENERATE

Domain: {domain}
Constructs: {constructs}
Claim: {claim}
Questions:"""


def build_question_prompt(constructs: list[str], domain: str, claim: str | None) -> str:
    """Build the hypothetical question generation prompt.

    constructs is the list of construct texts.
    domain is the resolved domain from QueryExpansion.
    claim is the asserted claim text, or None if the query had no claim.
    """
    return QUESTION_PROMPT.format(
        domain=domain,
        constructs=", ".join(constructs),
        claim=claim or "none",
    )
