"""Dokument-Generierung: Word (Anlage zur VRA) + HTML (interner Bericht)."""

from app.documents.html_report import build_html_report
from app.documents.word_builder import build_word_anlage

__all__ = ["build_html_report", "build_word_anlage"]
