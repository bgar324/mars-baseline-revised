import textwrap
import langextract as lx


PROMPT = textwrap.dedent(
    """\
    Decompose a research query into semantic spans. The input is one research question or idea, not a paper. Return each extracted span with its role and exact text.

    ## ROLES

    1. domain - the scholarly field named in the query. Extract it only when the query explicitly names a field or uses a field label as context. Do not infer a domain from general topic words alone.
    2. goal - the phrase that states the query's investigative intent. Extract the literal phrase from the text and set the `intent` attribute to exactly one of:
       - "descriptive": characterizes a state, prevalence, taxonomy, or phenomenon.
       - "associative": tests a correlation, link, distinction, or prediction between constructs.
       - "causal": tests an effect, mechanism, or directed pathway.
    3. construct - a theoretical entity, variable, population, outcome, mechanism, or concept the query is built from. Extract every distinct construct. This includes a construct in a "through ..." or "via ..." position.
    4. claim - the proposition under investigation: a complete relation over constructs stated with a relational verb. Extract it only when the query contains a recoverable proposition, even if the query asks whether it holds.

    ## RULES

    - Assign the role a span plays in this query, not the kind of thing the span is in general.
    - Distinguish construct from claim: a construct is one noun phrase; a claim is a full proposition relating constructs.
    - Set the goal span to the literal phrase in the text. Set `intent` to one fixed label.
    - Do not extract connectives or scaffolding phrases by themselves, including "through", "via", "between", "the effect of", "this study", or "we investigate".
    - Extract at least one construct from every query, usually two or more.
    - Extract domain, goal, and claim at most once each. Any of them may be absent.
    - Extract exact text with no surrounding punctuation.
    - For "Full Name (ACRONYM)", extract only the full name.
    - Spans may overlap. A claim will often contain its constructs.

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
