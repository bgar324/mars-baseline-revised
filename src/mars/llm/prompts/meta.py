SYSTEM_INSTRUCTION = """Synthesize a citation-grounded cluster of papers into one debating agent that represents the research community shared across the cluster's papers, not any single paper or lab. The agent joins a multi-agent debate on a focal claim.

# WRITE methods_summary FIRST
Write methods_summary from the sample papers and the given fields-of-study and publication types. State the cluster's common designs, data modalities, populations, and model or analysis families. methods_summary is the only field that may name specific datasets, named indices, named frameworks, or specific statistical methods.

# DATASET PLACEMENT
Write specific dataset names (for example ELSA, KNHANES), named indices or frameworks (for example Area Deprivation Index, allostatic load, Oaxaca-Blinder decomposition), and specific statistical techniques in methods_summary only. Do not write any of them in name, framing, background, or instructions.

# WRITE THE REMAINING FIELDS
- name: write "{Field} · {Facet}". Field is the broadest accurate discipline label. Facet is the one feature that distinguishes this cluster from other clusters in the same field: the specific mechanism, lens, scale, or sub-process the papers share. Write a specific facet (for example "Outlier-Dimension Geometry"), not a generic field term (do not write bare "Alignment", "Methods", or "Modeling"). Write at most 6 words total. Write no dataset or named index. Example: "Social Epidemiologist · Life-Course".
- framing: write one sentence stating how this community frames the focal claim. Name the claim's key variables and at most one high-level methodological anchor (for example "longitudinal cohorts"). Write no paradigm, dataset, or parameterization.
- background: write 1 to 3 sentences stating the methodological tradition and evidence base at the family level (for example "longitudinal cohorts and rodent stress paradigms; neuroimaging, endocrine and immune markers"). Name families of designs and measures. Write no specific dataset or index.
- reasoning_style: state how this community produces evidence, not what it studies.
- evaluation_lens: state the standard this community applies when judging whether a hypothesis is worth pursuing.
- instructions: write 3 to 5 rules that govern how the agent argues in the debate: handling correlational versus causal evidence, weighing modalities or populations, treating conflicting evidence, and stating predictions. Write no specific method, dataset, or theoretical commitment. Write no meta-rule such as "cite the references". State the community's stance in framing, reasoning_style, and evaluation_lens, not here.

# BREADTH
Write name, framing, background, and instructions so they still apply if five more typical papers were added to the cluster. If they would not, broaden them."""


EXAMPLE = """EXAMPLE
FOCAL CLAIM: Chronic stress alters immune function through epigenetic mechanisms.
CLUSTER CONTEXT:
cluster size: 38 papers (representative sample below)
dominant fields of study: Biology, Medicine, Psychology
publication types: JournalArticle, Study
SAMPLE PAPERS:
- PTSD and DNA Methylation in Immune Function Gene Promoters
  TLDR: In deployed personnel who developed PTSD, IL18 promoter methylation increased post-deployment.
- Repressive histone methylation in cocaine-induced stress vulnerability
  TLDR: H3K9 methylation in nucleus accumbens mediates stress vulnerability after cocaine exposure.
- Acute Stress-Induced Epigenetic Modulations
  TLDR: Acute stress induces protective epigenetic processes in rodent hippocampus modulating IEG transcription.
Output:
{
  "methods_summary": "Preclinical rodent stress paradigms paired with human psychiatric cohorts; assays of DNA methylation and histone modifications in brain and peripheral immune tissue; mechanistic and biomarker designs.",
  "name": "Molecular Psychiatrist · Stress Epigenetics",
  "framing": "Stress shapes psychiatric outcomes through brain-anchored epigenetic regulation with detectable peripheral signatures.",
  "background": "Works across rodent stress models and clinical psychiatric cohorts, profiling stress-related neuroendocrine signaling, epigenetic regulation, and activity-dependent gene expression in brain-immune interactions.",
  "reasoning_style": "mechanistic",
  "evaluation_lens": "convergence",
  "instructions": [
    "Treat correlational findings as hypothesis-generating, not confirmatory.",
    "Require agreement across animal mechanism and human biomarker before strongly endorsing a hypothesis.",
    "Weigh whether an effect seen in one tissue or species plausibly transfers to another.",
    "State what would be observed if your favored hypothesis holds."
  ]
}


}"""


def build_meta_cache_block(focal_claim: str) -> str:
    return (
        "Synthesize the cluster below into one debating persona.\n\n"
        f"{EXAMPLES}\n\n"
        "NOW SYNTHESIZE\n\n"
        f"FOCAL CLAIM: {focal_claim}"
    )


def build_meta_cluster_block(cluster_summary: str) -> str:
    return f"{cluster_summary}\n\nOutput:"


def build_meta_prompt(focal_claim: str, cluster_summary: str) -> str:
    return f"{build_meta_cache_block(focal_claim)}\n\n{build_meta_cluster_block(cluster_summary)}"


def build_generic_meta_block(focal_claim: str) -> str:
    return (
        "Invent ONE plausible research community that would engage the focal claim "
        "below and synthesize it into a field-level debating persona. You are given no "
        "cluster of papers - ground the persona in the focal claim and its domain alone, "
        "choosing a distinct discipline, framing, and evaluation lens a real community "
        "in this area would hold.\n\n"
        f"{EXAMPLES}\n\n"
        "NOW SYNTHESIZE\n\n"
        f"FOCAL CLAIM: {focal_claim}\n\nOutput:"
    )
