from core.pr_comment import render_pr_comment


def test_render_pr_comment_includes_regression_and_team_context():
    payload = {
        "regression": {
            "new_finding_count": 1,
            "resolved_finding_count": 1,
            "existing_finding_count": 5,
            "regression_detected": True,
            "new_findings": [
                {
                    "file_name": "core/scanner.py",
                    "line": 152,
                    "severity": "high",
                    "message": "Nested loop detected",
                    "team_context": {
                        "people": {
                            "owners": ["Joseph"],
                            "watchers": ["Alice"],
                            "influencing_members": ["Bob"],
                        },
                        "tasks": [
                            {
                                "id": "TASK-1",
                                "title": "Scanner cleanup",
                                "status": "in_progress",
                                "primary_owner": "Joseph",
                            }
                        ],
                        "notes": [
                            {
                                "id": "NOTE-1",
                                "body": "Please review this loop",
                            }
                        ],
                    },
                }
            ],
            "resolved_findings": [
                {
                    "file_name": "core/runtime_scanner.py",
                    "line": 20,
                    "severity": "medium",
                    "message": "Repeated expensive call",
                }
            ],
        }
    }

    text = render_pr_comment(payload)

    assert "Explainable Regression Report" in text
    assert "core/scanner.py:152" in text
    assert "Owners: Joseph" in text
    assert "TASK-1 | Scanner cleanup" in text
    assert "NOTE-1 | Please review this loop" in text
    assert "Resolved findings" in text
