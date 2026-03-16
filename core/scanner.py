import ast
from pathlib import Path

from config.settings import load_settings
from reporting.models import AnalysisReport


class ProjectInspector(ast.NodeVisitor):
    def __init__(self):
        self.findings = []
        self.scored_findings = []

    def visit_For(self, node):
        nested_for_found = False

        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.For):
                nested_for_found = True
                break

            for grandchild in ast.walk(child):
                if isinstance(grandchild, ast.For):
                    nested_for_found = True
                    break

            if nested_for_found:
                break

        if nested_for_found:
            self._add_finding(
                severity="high",
                line=node.lineno,
                message="Nested loop detected — possible O(n²) performance issue.",
            )

        call_names = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = _get_call_name(child)
                if call_name:
                    call_names.append(call_name)

        for call_name in sorted(set(call_names)):
            self._add_finding(
                severity="medium",
                line=node.lineno,
                message=f"Function call `{call_name}()` detected inside a loop — review for repeated expensive work.",
            )

        self.generic_visit(node)

    def visit_While(self, node):
        self._add_finding(
            severity="high",
            line=node.lineno,
            message="While-loop detected — review termination and repeated work carefully.",
        )

        call_names = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = _get_call_name(child)
                if call_name:
                    call_names.append(call_name)

        for call_name in sorted(set(call_names)):
            self._add_finding(
                severity="medium",
                line=node.lineno,
                message=f"Function call `{call_name}()` detected inside a loop — review for repeated expensive work.",
            )

        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "append":
            self._add_finding(
                severity="low",
                line=node.lineno,
                message="List append detected — consider list comprehension if appropriate.",
            )

        self.generic_visit(node)

    def _add_finding(self, severity: str, line: int, message: str):
        text = f"[{severity.upper()}] Line {line}: {message}"
        self.findings.append(text)
        self.scored_findings.append(
            {
                "severity": severity,
                "line": line,
                "message": message,
            }
        )


def _get_call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


def _overall_severity(scored_findings):
    if not scored_findings:
        return "low"

    severities = {item["severity"] for item in scored_findings}

    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def _severity_summary(scored_findings):
    counts = {"high": 0, "medium": 0, "low": 0}

    for item in scored_findings:
        counts[item["severity"]] += 1

    return counts


def scan_python_file(file_path) -> AnalysisReport:
    file_path = Path(file_path)

    report = AnalysisReport(
        title=f"Project scan for {file_path.name}",
        problem_type="StaticInspection",
        severity="warning",
        explanation="Static code inspection completed.",
        suspected_cause="Potential inefficiencies or risky structural patterns were detected.",
        confidence="medium",
        suggested_next_action="Review the inspection findings and optimize the flagged areas where needed.",
    )

    report.file_name = str(file_path)

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception as exc:
        report.severity = "critical"
        report.explanation = "The file could not be parsed successfully."
        report.suspected_cause = f"Parsing failed with {type(exc).__name__}: {exc}"
        report.confidence = "low"
        report.notes.append("This file may contain invalid Python syntax or an unsupported encoding.")
        return report

    inspector = ProjectInspector()
    inspector.visit(tree)

    report.inspection_findings = inspector.findings
    report.performance_scored_findings = inspector.scored_findings

    if inspector.findings:
        summary = _severity_summary(inspector.scored_findings)
        overall = _overall_severity(inspector.scored_findings)

        report.performance_overall_severity = overall
        report.performance_severity_summary = summary
        report.optimization_status = f"potential inefficiencies detected ({overall} severity)"
        report.optimization_notes = [
            f"{len(inspector.findings)} possible issue(s) found during static inspection.",
            f"Severity summary: high={summary['high']}, medium={summary['medium']}, low={summary['low']}.",
        ]
        report.observed_facts.append(f"Scanned file: {file_path.name}")
        report.observed_facts.append(f"Overall performance severity: {overall}")
    else:
        report.performance_overall_severity = "low"
        report.performance_severity_summary = {"high": 0, "medium": 0, "low": 0}
        report.performance_scored_findings = []
        report.optimization_status = "no obvious structural inefficiencies detected"
        report.optimization_notes = [
            "No nested loops, repeated append patterns, or function calls inside loops were detected by the current scanner.",
            "Severity summary: high=0, medium=0, low=0.",
        ]
        report.observed_facts.append(f"Scanned file: {file_path.name}")
        report.observed_facts.append("Overall performance severity: low")

    return report


def scan_project(project_path: str, config_path: str = "explainable.toml"):
    settings = load_settings(config_path)
    ignore_names = set(settings["scan"]["ignore"])

    base_path = Path(project_path)
    reports = []

    for file_path in base_path.rglob("*.py"):
        if any(part in ignore_names for part in file_path.parts):
            continue

        reports.append(scan_python_file(file_path))

    return reports