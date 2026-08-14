"""Interner Prüfbericht als HTML — enthält ALLES, was das Word NICHT darf.

Das ist das Debug-/Audit-Dokument für den Fachanwender: LLM-Rohantwort,
Confidence-Werte, Modell-Metadaten, Rule-Engine-Trace, Audit-Log. Dieses
Dokument geht NICHT an die Behörde.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.core.enums import DecisionCode, NvtStatus
from app.core.models import Nvt, Project
from app.core.repositories import AuditRepo


@dataclass
class HtmlReportResult:
    output_path: Path
    included_nvt_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_CSS = """
body {
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 1000px; margin: 2rem auto; padding: 0 1rem;
    color: #222; line-height: 1.5;
}
h1, h2, h3 { color: #111; }
h1 { border-bottom: 2px solid #dc2626; padding-bottom: 0.3rem; }
h2 { margin-top: 2.5rem; border-bottom: 1px solid #ddd; padding-bottom: 0.2rem; }
.warn {
    background: #fff5e6; border-left: 4px solid #dc9a26; padding: 0.6rem 1rem;
    margin: 1rem 0;
}
.meta {
    background: #f5f5f7; padding: 0.8rem 1rem; border-radius: 6px;
    font-size: 0.9rem;
}
table.kv { border-collapse: collapse; margin: 0.8rem 0; }
table.kv td { padding: 0.2rem 0.8rem; vertical-align: top; }
table.kv td:first-child { color: #555; font-weight: 600; }
details { margin: 0.4rem 0; }
summary { cursor: pointer; padding: 0.3rem 0; color: #444; }
pre.json {
    background: #1e1e1e; color: #ddd; padding: 0.8rem 1rem;
    border-radius: 4px; overflow-x: auto; font-size: 0.82rem;
}
.badge {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 12px;
    font-size: 0.8rem; font-weight: 600; margin-right: 0.4rem;
}
.b-green { background: #dcfce7; color: #166534; }
.b-yellow { background: #fef9c3; color: #854d0e; }
.b-red { background: #fee2e2; color: #991b1b; }
.b-gray { background: #f3f4f6; color: #374151; }
.audit li { font-size: 0.85rem; color: #555; margin: 0.2rem 0; }
.audit code { background: #eee; padding: 0.1rem 0.3rem; border-radius: 3px; }
"""


def _badge_class(code: str) -> str:
    if code in (
        DecisionCode.AUTO_FREIGABE_VORBEREITET.value,
        DecisionCode.PRIVATFLAECHE.value,
    ):
        return "b-green"
    if code == DecisionCode.AUTO_VORSCHLAG.value:
        return "b-yellow"
    if code in (
        DecisionCode.MANUELLE_PRUEFUNG.value,
        DecisionCode.WIDERSPRUCH.value,
        DecisionCode.NICHT_BEURTEILBAR.value,
        DecisionCode.REGELPLAN_NICHT_GEFUNDEN.value,
    ):
        return "b-red"
    return "b-gray"


def _fmt_json(obj) -> str:  # type: ignore[no-untyped-def]
    try:
        return html.escape(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    except Exception:
        return html.escape(str(obj))


def _address_line(nvt: Nvt) -> str:
    addr = nvt.address_json or {}
    parts = []
    if addr.get("street") or addr.get("house_number"):
        parts.append(f"{addr.get('street','')} {addr.get('house_number','')}".strip())
    if addr.get("postal_code") or addr.get("city"):
        parts.append(f"{addr.get('postal_code','')} {addr.get('city','')}".strip())
    return ", ".join(p for p in parts if p) or "—"


def _render_nvt(nvt: Nvt, audit: AuditRepo) -> str:
    parts: list[str] = []
    status = NvtStatus(nvt.status).value
    parts.append(f'<h2>NVT {html.escape(nvt.nvt_number)} '
                 f'<span class="badge b-gray">{status}</span></h2>')
    parts.append(f'<p><strong>Adresse:</strong> {html.escape(_address_line(nvt))}</p>')

    if nvt.decision is not None:
        code = nvt.decision.code.value if hasattr(nvt.decision.code, "value") else str(nvt.decision.code)
        parts.append(
            f'<p><strong>Regelplan:</strong> {html.escape(nvt.decision.selected_ruleplan_id or "—")} '
            f'<span class="badge {_badge_class(code)}">{html.escape(code)}</span></p>'
        )
        parts.append(
            '<table class="kv">'
            f'<tr><td>vision_confidence</td><td>{float(nvt.decision.vision_confidence):.2f}</td></tr>'
            f'<tr><td>rule_confidence</td><td>{float(nvt.decision.rule_confidence):.2f}</td></tr>'
            f'<tr><td>data_completeness</td><td>{float(nvt.decision.data_completeness):.2f}</td></tr>'
            f'<tr><td>human_review_required</td><td>{nvt.decision.human_review_required}</td></tr>'
            f'<tr><td>ruleset_version</td><td>{html.escape(nvt.decision.ruleset_version)}</td></tr>'
            f'<tr><td>ruleplan_revision_hash</td><td>{html.escape((nvt.decision.ruleplan_revision_hash or "—")[:16])}</td></tr>'
            f'<tr><td>model_id</td><td>{html.escape(nvt.decision.model_id or "—")}</td></tr>'
            f'<tr><td>prompt_hash</td><td>{html.escape((nvt.decision.prompt_hash or "—")[:16])}</td></tr>'
            "</table>"
        )
        if nvt.decision.reasons:
            parts.append("<p><strong>Begründungen:</strong></p><ul>")
            for r in nvt.decision.reasons:
                parts.append(f"<li>{html.escape(r)}</li>")
            parts.append("</ul>")
        if nvt.decision.warnings:
            parts.append('<div class="warn"><strong>Warnungen:</strong><ul>')
            for w in nvt.decision.warnings:
                parts.append(f"<li>{html.escape(w)}</li>")
            parts.append("</ul></div>")

    if nvt.environment is not None:
        parts.append("<details><summary>EnvironmentAnalysis — raw_provider_output (LLM-Rohantwort)</summary>")
        parts.append(f'<pre class="json">{_fmt_json(nvt.environment.raw_provider_output)}</pre>')
        parts.append("</details>")

    if nvt.ruleplan_candidates:
        parts.append("<details><summary>Rule-Engine-Kandidaten</summary><ul>")
        for cand in sorted(nvt.ruleplan_candidates, key=lambda c: c.rank):
            parts.append(
                f"<li><strong>{html.escape(cand.ruleplan_id)}</strong> — "
                f"Rank {cand.rank}, Score {float(cand.score):.2f}, "
                f"{len(cand.matched_predicates)} Prädikate erfüllt, "
                f"{len(cand.unmet_requirements)} offene Voraussetzungen</li>"
            )
        parts.append("</ul></details>")

    if nvt.decision is not None and nvt.decision.trace_json:
        parts.append("<details><summary>Rule-Engine-Trace</summary>")
        parts.append(f'<pre class="json">{_fmt_json(nvt.decision.trace_json)}</pre>')
        parts.append("</details>")

    # Audit
    entries = audit.list_for_nvt(nvt.id, limit=40)
    if entries:
        parts.append('<details><summary>Audit-Log</summary><ul class="audit">')
        for e in entries:
            ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            user = html.escape(e.user or "system")
            old = f"<code>{html.escape(e.old_value or '')}</code>" if e.old_value else ""
            new = f"<code>{html.escape(e.new_value or '')}</code>" if e.new_value else ""
            arrow = " → " if e.old_value and e.new_value else ""
            parts.append(
                f'<li>{ts} · <em>{user}</em> · '
                f'<code>{html.escape(e.action)}</code> {old}{arrow}{new}</li>'
            )
        parts.append("</ul></details>")

    return "\n".join(parts)


def build_html_report(
    project: Project,
    nvts: list[Nvt],
    audit: AuditRepo,
    output_path: Path,
) -> HtmlReportResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    body_parts: list[str] = []
    body_parts.append(f"<h1>Interner Prüfbericht — {html.escape(project.name)}</h1>")
    body_parts.append(
        '<div class="warn"><strong>NUR INTERN.</strong> Dieser Bericht enthält '
        "LLM-Rohantworten, Confidence-Werte und Modell-Metadaten. Er ist NICHT "
        "der Behörde vorzulegen — dafür gibt es die Word-Anlage."
        "</div>"
    )
    body_parts.append(
        f'<p class="meta">Generiert: {generated}<br>Auftragnehmer: '
        f'{html.escape(project.contractor)}<br>Regelwerks-Version: '
        f'{html.escape(project.ruleset_version)}</p>'
    )

    included: list[str] = []
    for nvt in nvts:
        body_parts.append(_render_nvt(nvt, audit))
        included.append(str(nvt.id))

    # Projekt-Audit-Log am Ende
    project_events = audit.list_for_project(project.id, limit=100)
    if project_events:
        body_parts.append('<h2>Projekt-Audit-Log</h2><ul class="audit">')
        for e in project_events:
            ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            user = html.escape(e.user or "system")
            body_parts.append(
                f'<li>{ts} · <em>{user}</em> · <code>{html.escape(e.action)}</code></li>'
            )
        body_parts.append("</ul>")

    html_out = (
        "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
        f"<title>Interner Prüfbericht — {html.escape(project.name)}</title>"
        f"<style>{_CSS}</style></head><body>"
        + "\n".join(body_parts)
        + "</body></html>"
    )
    output_path.write_text(html_out, encoding="utf-8")
    return HtmlReportResult(output_path=output_path, included_nvt_ids=included)
