import textwrap
import langextract as lx


PROMPT = textwrap.dedent(
    """\
    You are a PhD researcher decomposing a research query into its semantic roles. The input is a single research question or research idea, not a paper. Return each span with its role and exact text.

    ## SEMANTIC ROLES:

    1. domain - The field or area of study the query sits in.
       Examples: neuroimmunology, computational linguistics, medicinal chemistry
       Often implicit. Extract only if the query names or strongly implies a field.
       Do NOT invent a domain that is not present in the text.

    2. goal - The investigative intent of the query.
       Extract the syntactic phrase that signals the intent as the span
       (how does, what are, do, why, to what extent).
       Record the intent in the `intent` attribute. It MUST be exactly one of:
       - "descriptive": characterizing a state, prevalence, or phenomenon.
       - "associative": testing a correlation, link, or prediction between constructs.
       - "causal": testing a mechanism, effect, or directed pathway.

    3. construct - A theoretical entity, variable, or concept the query is built from.
       Examples: chronic stress, immune function, epigenetic mechanisms, working memory
       These are the things the query asks about or routes through.
       Extract every distinct construct, including the one in an explanatory
       "through / via ___" position.

    4. claim - A complete proposition the query asserts or presupposes.
       Examples: stress alters immune function via epigenetic mechanisms
       A claim is a relation stated over constructs. Extract only if the query
       actually asserts or presupposes a proposition.

    ## CRITICAL RULES:

    ### ROLE IS POSITIONAL:
    Assign the role a span plays in this query, not the kind of thing it is.
    The same term can be a construct in one query and absent in another.

    ### CONSTRUCT vs CLAIM:
    A construct is one entity or variable (a noun phrase): "chronic stress".
    A claim is a full proposition relating constructs (has a relational verb):
    "stress alters immunity". Extract a claim only if the query asserts one;
    open and descriptive questions usually have none.

    ### GOAL SPAN vs INTENT:
    The goal span is the literal syntactic phrase, located in the text.
    The intent attribute is the inferred category. The span is grounded;
    the intent is one of the three fixed labels.

    ### DO NOT EXTRACT:
    - Connectives: through, via, between, the effect of
    - Meta-phrases: this study, we investigate

    ### HOW MANY TO EXPECT:
    Every query has at least one construct, usually two or more.
    Domain, goal, and claim each appear at most once, and may be absent.

    ### SPANS:
    - Use exact text, no surrounding punctuation
    - For "Full Name (ACRONYM)", extract only the full name
    - Spans may overlap; a claim normally contains its constructs

    ## OUTPUT FORMAT:
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
