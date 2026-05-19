import re
import unicodedata
from collections import Counter


def normalize_ligatures(text: str) -> str:
    """Decompose ligatures (e.g., 'ﬁ' -> 'fi')."""
    return unicodedata.normalize("NFC", text)


def remove_citations(text: str) -> str:
    """Remove in-line citations, 'et al.' mentions, and footnotes."""
    text = re.sub(r"\s?\([^)]*?\d{4}[^)]*?\)", "", text)
    text = re.sub(r"\b[A-Z][a-zA-Z\-]+\s+et al\.?\b", "", text)
    text = re.sub(r"foot_\d+", "", text)
    text = re.sub(r" {2,}", " ", text)
    return text


def remove_bullets(text: str) -> str:
    """Remove common bullet point markers."""
    text = re.sub(r"•\s?", "", text)
    text = re.sub(r"^\s*[\*\-]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+[\*\-]\s+", " ", text)
    return text


def separate_references(text: str) -> str:
    """Insert a space between text and numbers (e.g., Figure1 -> Figure 1)."""
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d\.)([A-Za-z])", r"\1 \2", text)
    return text


def dehyphenate(text: str) -> str:
    """Remove line-break hyphens from PDF parsing."""
    text = re.sub(r"(\w+)-\s*\n\s*([a-z])", r"\1\2", text)
    text = re.sub(r"(\w+)- ([a-z])", r"\1\2", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Fix irregular spacing from PDF parsing."""
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def fix_concatenation(text: str) -> str:
    """Fix concatenation errors while preserving intentional camelCase."""
    text = re.sub(r"\b([A-Z])\1([a-z])", r"\1\2", text)
    text = re.sub(r"([a-z]{3,})([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z]{2,})([A-Z])", r"\1 \2", text)
    return text


def fix_repeated_capitals(text: str, known_terms: set[str] | None = None) -> str:
    """Fix doubled capital letters from parsing errors."""
    if known_terms is None:
        known_terms = set()

    def replace_doubled(match: re.Match[str]) -> str:
        full_word = match.group(0)
        if full_word in known_terms:
            return full_word
        return re.sub(r"([A-Z])\1", r"\1", full_word)

    return re.sub(r"\b[A-Z][A-Za-z]+\b", replace_doubled, text)


def clean_punctuation_artifacts(text: str) -> str:
    """Remove punctuation artifacts from text parsing."""
    text = re.sub(r"[;,]\s*[;,]+", ",", text)
    text = re.sub(r"\s+[;,]\s+", " ", text)
    text = re.sub(r"\(\s*[;,]+\s*\)", "", text)
    text = re.sub(r"([.,:;-])\1{3,}", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def remove_urls(text: str) -> str:
    """Remove URLs and web addresses."""
    return re.sub(r"https?://\S+|www\.\S+", "", text)


def remove_repeated_text(text: str, threshold_ratio: float = 0.1) -> str:
    """Remove repeated headers/footers from multi-page extraction."""
    lines = text.split("\n")
    line_counts = Counter(lines)
    threshold = max(1, int(len(lines) * threshold_ratio))
    cleaned = [
        line
        for line in lines
        if line_counts[line] <= threshold or line.strip() == ""
    ]
    return "\n".join(cleaned)


def resolve_abbreviations(text: str, abbrev_dict: dict[str, str]) -> str:
    """Resolve common abbreviations using a lookup dict."""
    for abbrev, full_form in abbrev_dict.items():
        text = re.sub(rf"\b{re.escape(abbrev)}\b", full_form, text)
    return text


def preprocess_section(
    text: str,
    abbrev_dict: dict[str, str] | None = None,
    known_terms: set[str] | None = None,
) -> str:
    """Apply the minimal preprocessing pipeline for a text section."""
    text = normalize_ligatures(text)
    text = remove_citations(text)
    text = remove_bullets(text)
    text = separate_references(text)
    text = dehyphenate(text)
    text = normalize_whitespace(text)
    text = fix_concatenation(text)
    text = fix_repeated_capitals(text, known_terms)
    text = clean_punctuation_artifacts(text)
    text = remove_urls(text)

    if abbrev_dict is not None:
        text = resolve_abbreviations(text, abbrev_dict)

    return re.sub(r"\s+", " ", text).strip()


def preprocess_document(
    text: str,
    remove_repeated: bool = True,
    abbrev_dict: dict[str, str] | None = None,
    known_terms: set[str] | None = None,
) -> str:
    """Apply full document preprocessing with optional header/footer removal."""
    if remove_repeated:
        text = remove_repeated_text(text)

    text = normalize_ligatures(text)
    text = remove_citations(text)
    text = remove_bullets(text)
    text = separate_references(text)
    text = dehyphenate(text)
    text = normalize_whitespace(text)
    text = fix_concatenation(text)
    text = fix_repeated_capitals(text, known_terms)
    text = clean_punctuation_artifacts(text)
    text = remove_urls(text)

    if abbrev_dict is not None:
        text = resolve_abbreviations(text, abbrev_dict)

    return re.sub(r"\s+", " ", text).strip()
