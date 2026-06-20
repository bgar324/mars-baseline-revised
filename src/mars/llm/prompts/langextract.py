import textwrap
import langextract as lx


PROMPT = textwrap.dedent(
    """\
    Decompose a research query into its semantic roles. The input is a single research question or idea, not a paper. Return each span with its role and exact text.

    ## ROLES

    1. domain - the field the query names (e.g. neuroimmunology, computational linguistics). Extract only if the query names it or strongly implies it. Do not invent a domain.
    2. goal - the investigative intent. Extract the phrase that signals it (how does, what are, do, why, to what extent) as the span, and set the `intent` attribute to exactly one of:
       - "descriptive": characterizes a state, prevalence, or phenomenon.
       - "associative": tests a correlation, link, or prediction between constructs.
       - "causal": tests a mechanism, effect, or directed pathway.
    3. construct - a theoretical entity, variable, or concept the query is built from (e.g. chronic stress, working memory). Extract every distinct construct, including a construct in a "through ___" or "via ___" position.
    4. claim - a complete proposition the query asserts or presupposes: a relation over constructs stated with a relational verb. Extract only if the query asserts one.

    ## RULES

    - Assign the role a span plays in this query, not the kind of thing the span is.
    - Distinguish construct from claim: a construct is one noun phrase ("chronic stress"); a claim is a full proposition ("stress alters immunity"). Open and descriptive questions usually have no claim.
    - Set the goal span to the literal phrase in the text; set `intent` to one of the three fixed labels.
    - Do not extract connectives (through, via, between, the effect of) or meta-phrases (this study, we investigate).
    - Extract at least one construct from every query, usually two or more. Extract domain, goal, and claim at most once each; each may be absent.
    - Extract exact text with no surrounding punctuation. For "Full Name (ACRONYM)" extract only the full name. Spans may overlap (a claim normally contains its constructs).

    Return spans in order of appearance with role and exact text.
    """
)


EXAMPLES = [
    lx.data.ExampleData(
        text="How does chronic stress alter immune function through epigenetic mechanisms?",
        extractions=[
            lx.data.Extraction(
                extraction_class="goal",
                extraction_text="How does",
                attributes={"intent": "causal"},
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="chronic stress"
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="immune function"
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="epigenetic mechanisms"
            ),
            lx.data.Extraction(
                extraction_class="claim",
                extraction_text="chronic stress alter immune function through epigenetic mechanisms",
            ),
        ],
    ),
    lx.data.ExampleData(
        text="What are the gut microbiome signatures of long-COVID patients?",
        extractions=[
            lx.data.Extraction(
                extraction_class="goal",
                extraction_text="What are",
                attributes={"intent": "descriptive"},
            ),
            lx.data.Extraction(
                extraction_class="construct",
                extraction_text="gut microbiome signatures",
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="long-COVID patients"
            ),
        ],
    ),
    lx.data.ExampleData(
        text="In psychoneuroimmunology, is social media use associated with adolescent depression?",
        extractions=[
            lx.data.Extraction(
                extraction_class="domain", extraction_text="psychoneuroimmunology"
            ),
            lx.data.Extraction(
                extraction_class="goal",
                extraction_text="is",
                attributes={"intent": "associative"},
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="social media use"
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="adolescent depression"
            ),
            lx.data.Extraction(
                extraction_class="claim",
                extraction_text="social media use associated with adolescent depression",
            ),
        ],
    ),
    lx.data.ExampleData(
        text="Characterize the binding affinity of novel kinase inhibitors.",
        extractions=[
            lx.data.Extraction(
                extraction_class="goal",
                extraction_text="Characterize",
                attributes={"intent": "descriptive"},
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="binding affinity"
            ),
            lx.data.Extraction(
                extraction_class="construct", extraction_text="novel kinase inhibitors"
            ),
        ],
    ),
]
