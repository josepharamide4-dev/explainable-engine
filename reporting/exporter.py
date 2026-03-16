import json
from dataclasses import asdict
from pathlib import Path

from reporting.formatter import format_report
from reporting.models import AnalysisReport


def export_report_text(report: AnalysisReport, output_path: str) -> None:
    path = Path(output_path)
    path.write_text(format_report(report), encoding="utf-8")


def export_report_json(report: AnalysisReport, output_path: str) -> None:
    path = Path(output_path)
    data = asdict(report)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def export_reports_text(reports: list[AnalysisReport], output_path: str) -> None:
    path = Path(output_path)
    sections = []

    for index, report in enumerate(reports, start=1):
        sections.append(f"{'=' * 20} Report {index} {'=' * 20}")
        sections.append(format_report(report))

    path.write_text("\n\n".join(sections), encoding="utf-8")


def export_reports_json(reports: list[AnalysisReport], output_path: str) -> None:
    path = Path(output_path)
    data = [asdict(report) for report in reports]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")