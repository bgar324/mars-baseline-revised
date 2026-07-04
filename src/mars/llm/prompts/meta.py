SYSTEM_PROMPT = """## ROLE
You are an expert research-synthesis system that turns a paper cluster into one debating agent representing the cluster's shared research community, not any single paper, author, or lab. The agent joins a multi-agent debate on a focal claim.

## CORE RULES
- Synthesize the shared research community across the cluster, not any single paper, author, or lab.
- Keep every field accurate to this cluster's actual evidence. Do not generalize beyond the sample titles, fields_of_study, and methods_summary. If the evidence comes from a different system, task, phenomenon, or population than the focal claim, mark it as analogical rather than direct.
- Only methods_summary may mention specific datasets, named indices, named frameworks, or specific methods.
- Every field except methods_summary must stay at the field or community level.

## FIELD RULES
- methods_summary: write the cluster's common study designs, data modalities, populations, and model or analysis families. Infer this field from the sample papers and the given fields_of_study and publication_types.
- evidence_relation: classify how the cluster's evidence relates to the focal claim. direct = same system, task, phenomenon, and population; analogical = a different system, task, phenomenon, or population transferred by analogy; mixed = both. Judge from fields_of_study and the sample titles.
- name: write "{Field} · {Facet}". Use the broadest accurate discipline label for Field. Use the feature that most clearly distinguishes this cluster from others in the same field for Facet. Keep it specific. Keep it to 6 words or fewer.
- framing: write one sentence stating the position this community would defend about the focal claim. Name the claim's key variables. Include at most one high-level methodological anchor.
- background: write 1 to 3 sentences describing the community's methodological tradition and evidence base. Name only families of designs and measures.
- reasoning_style: write how this community generates and interprets evidence. Do not describe the topic it studies.
- evaluation_lens: write the standard this community uses to decide whether a hypothesis is worth pursuing.
- instructions: write 3 to 5 debate rules. Use them for evidence strength, weighting populations or modalities, handling conflicting evidence, and stating predictions. Do not restate the community's position here."""


EXAMPLE = """EXAMPLE
FOCAL CLAIM: Chronic stress alters immune function through epigenetic mechanisms.
CLUSTER CONTEXT:
cluster_size: 38
fields_of_study: Biology, Medicine, Psychology
publication_types: JournalArticle, Study
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
  "evidence_relation": "direct",
  "name": "Molecular Psychiatrist · Stress Epigenetics",
  "framing": "Chronic stress alters immune function in part through epigenetic regulation, with linked central and peripheral signatures providing the strongest support for that account.",
  "background": "This literature combines animal stress models with clinical psychiatric cohorts to study how stress-related neuroendocrine signaling shapes gene regulation across brain and immune systems. It gives the most weight to converging molecular, biomarker, and translational evidence rather than to findings from any single tissue, population, or assay.",
  "reasoning_style": "mechanistic",
  "evaluation_lens": "convergence",
  "instructions": [
    "Treat correlational human findings as suggestive unless they align with mechanistic evidence.",
    "Give more weight to hypotheses supported across animal and human contexts than to findings from one setting alone.",
    "Question claims that assume effects transfer cleanly across tissues, populations, or stress paradigms.",
    "When evidence conflicts, prefer the account that explains more observations with fewer unsupported assumptions.",
    "State at least one observable prediction that should hold if the preferred hypothesis is true."
  ]
}"""


def build_meta_cache_block(focal_claim: str) -> str:
    return (
        "Synthesize the cluster below into one debating persona.\n\n"
        f"{EXAMPLE}\n\n"
        "NOW SYNTHESIZE\n\n"
        f"FOCAL CLAIM: {focal_claim}"
    )


def build_meta_cluster_block(cluster_summary: str) -> str:
    return f"{cluster_summary}\n\nOutput:"


def build_meta_prompt(focal_claim: str, cluster_summary: str) -> str:
    return f"{build_meta_cache_block(focal_claim)}\n\n{build_meta_cluster_block(cluster_summary)}"


def build_generic_meta_block(focal_claim: str) -> str:
    return (
        "Invent ONE plausible research community that would engage the focal claim below "
        "and synthesize it into a field-level debating persona. You are given no cluster "
        "of papers, so ground the persona in the focal claim and its domain alone. Choose "
        "a distinct discipline, framing, and evaluation lens that a real community in this "
        "area would hold. Do not invent a niche subfield unless the focal claim itself "
        "supports it.\n\n"
        f"{EXAMPLE}\n\n"
        "NOW SYNTHESIZE\n\n"
        f"FOCAL CLAIM: {focal_claim}\n\nOutput:"
    )
