"""Lightweight shared types used across module boundaries."""

from typing import NewType

PdfBytes = NewType("PdfBytes", bytes)
TeiBytes = NewType("TeiBytes", bytes)

# xml:id keys in Article.citations and Article.tables
CitationId = NewType("CitationId", str)
