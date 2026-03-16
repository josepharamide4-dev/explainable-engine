from dataclasses import dataclass, field
from typing import Any, Dict, List
import hashlib


def make_finding_id(
    file_name: str,
    line_number: int,
    category: str,
    message: str,
) -> str:
    raw = f"{file_name}|{line_number}|{category}|{message}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


@dataclass
class AnalysisReport:
    # Core report fields
    title: str = ""
    problem_type: str = ""
    severity: str = ""
    explanation: str = ""
    suspected_cause: str = ""
    confidence: str = ""
    suggested_next_action: str = ""

    # Location fields
    file_name: str = ""
    line_number: int = 0
    code_line: str = ""

    # Common narrative/report fields
    observed_facts: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)

    # Risk / recommendation compatibility fields
    bug_risks: List[str] = field(default_factory=list)
    possible_risks: List[str] = field(default_factory=list)
    risk_level: str = ""

    recommendations: List[str] = field(default_factory=list)
    possible_solutions: List[str] = field(default_factory=list)
    recommended_solution: str = ""
    recommended_solutions: List[str] = field(default_factory=list)

    # Runtime / trace compatibility fields
    root_cause: str = ""
    root_cause_trace: List[str] = field(default_factory=list)
    branch_trace: List[str] = field(default_factory=list)
    call_trace: List[str] = field(default_factory=list)
    variable_states: List[str] = field(default_factory=list)
    related_functions: List[str] = field(default_factory=list)

    error_type: str = ""
    error_message: str = ""
    stack_trace: List[str] = field(default_factory=list)
    execution_summary: str = ""
    reproduction_steps: List[str] = field(default_factory=list)

    # Static / inspection fields
    inspection_findings: List[str] = field(default_factory=list)

    # Optimization / performance fields
    optimization_status: str = ""
    optimization_notes: List[str] = field(default_factory=list)

    performance_overall_severity: str = ""
    performance_severity_summary: Dict[str, int] = field(
        default_factory=lambda: {"high": 0, "medium": 0, "low": 0}
    )
    performance_scored_findings: List[Dict[str, Any]] = field(default_factory=list)

    # Aggregate/export convenience fields
    report_count: int = 0
    reports: List[Dict[str, Any]] = field(default_factory=list)
    status: str = ""

    def add_performance_finding(
        self,
        severity: str,
        line: int,
        message: str,
        category: str = "performance",
    ):
        finding_id = make_finding_id(
            file_name=self.file_name,
            line_number=line,
            category=category,
            message=message,
        )

        self.performance_scored_findings.append(
            {
                "id": finding_id,
                "severity": severity,
                "line": line,
                "category": category,
                "message": message,
            }
        )

        if severity not in self.performance_severity_summary:
            self.performance_severity_summary[severity] = 0

        self.performance_severity_summary[severity] += 1

        rank = {"": 0, "low": 1, "medium": 2, "high": 3}
        if rank.get(severity, 0) > rank.get(self.performance_overall_severity, 0):
            self.performance_overall_severity = severity

        if not self.risk_level:
            self.risk_level = severity

    def __getattr__(self, name: str):
        """
        Backward-compatibility fallback for older code paths/tests that expect
        legacy report attributes not explicitly defined above.
        """
        if name.endswith("_trace") or name.endswith("_steps") or name.endswith("_states"):
            value = []
        elif name.endswith("_findings") or name.endswith("_facts") or name.endswith("_items"):
            value = []
        elif name.endswith("_functions") or name.endswith("_solutions") or name.endswith("_risks"):
            value = []
        elif name.startswith("possible_") or name.startswith("recommended_"):
            value = []
        elif name in {
            "summary",
            "details",
            "message",
            "description",
            "risk_level",
            "root_cause",
            "error_type",
            "error_message",
            "execution_summary",
            "recommended_solution",
        }:
            value = ""
        else:
            value = ""

        object.__setattr__(self, name, value)
        return value