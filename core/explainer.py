from reporting.models import AnalysisReport


def _base_report(
    title: str,
    problem_type: str,
    severity: str = "critical",
    confidence: str = "medium",
    function_name: str | None = None,
    error_message: str | None = None,
    variable_details: dict | None = None,
) -> AnalysisReport:
    report = AnalysisReport(
        title=title,
        problem_type=problem_type,
        severity=severity,
        confidence=confidence,
    )

    if function_name:
        report.observed_facts.append(f"Failing function: {function_name}")

    if error_message:
        report.observed_facts.append(f"Original error message: {error_message}")

    variable_details = variable_details or {}
    for name, value in variable_details.items():
        report.observed_facts.append(f"Variable `{name}` had value {value!r}")

    return report


def explain_type_error(
    error_message: str,
    function_name: str | None = None,
    variable_details: dict | None = None,
) -> AnalysisReport:
    report = _base_report(
        title="Type mismatch during execution",
        problem_type="TypeError",
        function_name=function_name,
        error_message=error_message,
        variable_details=variable_details,
    )

    if "NoneType" in error_message:
        report.explanation = (
            "An operation failed because a missing value was used where a real value was expected."
        )
        report.suspected_cause = (
            "A variable with value None reached logic that expected a valid object or number."
        )
        report.suggested_next_action = (
            "Check where the None value was introduced before this operation."
        )
        report.possible_solutions = [
            "Add a check for None before performing the operation.",
            "Ensure the variable is assigned a real numeric or object value earlier.",
            "Use a fallback value only if that matches the intended behavior.",
        ]
        report.recommended_solution = (
            "Validate the value before the operation and trace where None was introduced."
        )
        report.possible_risks = [
            "Using a fallback value may hide the real upstream data problem.",
            "Only checking at the failure point may leave similar bugs elsewhere.",
        ]
        report.risk_level = "medium"
    else:
        report.explanation = (
            "The operation failed because Python received a value of the wrong type."
        )
        report.suspected_cause = (
            "At least one input did not match the type expected by the code."
        )
        report.suggested_next_action = (
            "Inspect the values entering this operation and confirm their types."
        )
        report.possible_solutions = [
            "Check the types of all inputs before the operation.",
            "Convert inputs to the expected type before use.",
            "Add validation earlier so invalid types are rejected sooner.",
        ]
        report.recommended_solution = (
            "Add type validation before the operation so incorrect inputs are caught early."
        )
        report.possible_risks = [
            "Automatic conversion may change behavior in unexpected ways.",
            "Late validation may still allow bad data to spread through the program.",
        ]
        report.risk_level = "medium"

    return report


def explain_index_error(
    error_message: str,
    function_name: str | None = None,
    variable_details: dict | None = None,
) -> AnalysisReport:
    report = _base_report(
        title="List or sequence access failed",
        problem_type="IndexError",
        function_name=function_name,
        error_message=error_message,
        variable_details=variable_details,
    )

    variable_details = variable_details or {}
    for name, value in variable_details.items():
        if hasattr(value, "__len__"):
            try:
                report.observed_facts.append(f"Variable `{name}` length was {len(value)}")
            except TypeError:
                pass

    if "list index out of range" in error_message.lower():
        report.explanation = (
            "The code tried to access a position in a list or sequence that does not exist."
        )
        report.suspected_cause = (
            "The code assumed the collection had more items than it actually had."
        )
        report.suggested_next_action = (
            "Check why the collection was shorter than expected before indexing into it."
        )
        report.possible_solutions = [
            "Check that the collection is not empty before using an index.",
            "Confirm that the requested index is within the valid range.",
            "Populate the collection earlier if it is expected to contain items.",
        ]
        report.recommended_solution = (
            "Add a guard check before indexing and verify why the collection is empty or too short."
        )
        report.possible_risks = [
            "Skipping access when the list is empty may hide a data-loading bug.",
            "Using a default item may produce misleading downstream results.",
        ]
        report.risk_level = "medium"
    else:
        report.explanation = (
            "The code tried to access an invalid position in a sequence."
        )
        report.suspected_cause = (
            "The index used by the code did not match the available range of items."
        )
        report.suggested_next_action = (
            "Inspect the collection size and the index value used at the failure point."
        )
        report.possible_solutions = [
            "Validate the index before accessing the sequence.",
            "Adjust the logic that computes the index.",
            "Check whether the sequence length changed unexpectedly.",
        ]
        report.recommended_solution = (
            "Validate the index against the sequence length before access."
        )
        report.possible_risks = [
            "Only clamping the index may hide incorrect index calculations.",
        ]
        report.risk_level = "low"

    return report


def explain_key_error(
    error_message: str,
    function_name: str | None = None,
    variable_details: dict | None = None,
) -> AnalysisReport:
    report = _base_report(
        title="Missing dictionary key",
        problem_type="KeyError",
        function_name=function_name,
        error_message=error_message,
        variable_details=variable_details,
    )

    variable_details = variable_details or {}
    for name, value in variable_details.items():
        if isinstance(value, dict):
            report.observed_facts.append(
                f"Variable `{name}` has keys: {list(value.keys())}"
            )

    report.explanation = (
        "The code tried to access a dictionary key that was not present."
    )
    report.suspected_cause = (
        "The code expected a key to exist, but that key was missing from the data."
    )
    report.suggested_next_action = (
        "Check whether the missing key should have been added earlier or validated before access."
    )
    report.possible_solutions = [
        "Check that the key exists before accessing it.",
        "Use .get() with a safe default if that matches the intended behavior.",
        "Make sure the key is added to the dictionary earlier in the flow.",
    ]
    report.recommended_solution = (
        "Validate the dictionary contents before access and ensure required keys are present."
    )
    report.possible_risks = [
        "Using .get() with a default may hide missing required data.",
        "Adding keys late may still leave inconsistent dictionary state elsewhere.",
    ]
    report.risk_level = "medium"
    return report


def explain_attribute_error(
    error_message: str,
    function_name: str | None = None,
    variable_details: dict | None = None,
) -> AnalysisReport:
    report = _base_report(
        title="Object attribute access failed",
        problem_type="AttributeError",
        function_name=function_name,
        error_message=error_message,
        variable_details=variable_details,
    )

    if "NoneType" in error_message:
        report.explanation = (
            "The code tried to use an attribute or method on a missing value."
        )
        report.suspected_cause = (
            "A variable with value None was treated like a real object."
        )
        report.suggested_next_action = (
            "Check where the None value was introduced before this attribute access."
        )
        report.possible_solutions = [
            "Check that the value is not None before calling methods on it.",
            "Assign the variable a valid object earlier in the flow.",
            "Add validation where the value is first produced.",
        ]
        report.recommended_solution = (
            "Validate the value before attribute access and trace where None was introduced."
        )
        report.possible_risks = [
            "Guarding the attribute access may hide why the value became None.",
            "Replacing None with a placeholder object may change later behavior.",
        ]
        report.risk_level = "medium"
    else:
        report.explanation = (
            "The code tried to use an attribute or method that the object does not have."
        )
        report.suspected_cause = (
            "The object was not the type the code expected, or the attribute name was incorrect."
        )
        report.suggested_next_action = (
            "Check the object type at the failure point and confirm the attribute name is valid."
        )
        report.possible_solutions = [
            "Confirm the object is the expected type before attribute access.",
            "Check whether the attribute name is misspelled.",
            "Convert the object to the correct type earlier in the flow.",
        ]
        report.recommended_solution = (
            "Validate the object type before attribute access and confirm the attribute name."
        )
        report.possible_risks = [
            "Converting objects automatically may hide bad input assumptions.",
            "Changing attribute names without checking callers may break other code.",
        ]
        report.risk_level = "low"

    return report


def explain_error(
    error_type: str,
    error_message: str,
    function_name: str | None = None,
    variable_details: dict | None = None,
) -> AnalysisReport:
    handlers = {
        "TypeError": explain_type_error,
        "IndexError": explain_index_error,
        "KeyError": explain_key_error,
        "AttributeError": explain_attribute_error,
    }

    handler = handlers.get(error_type)
    if handler:
        return handler(
            error_message=error_message,
            function_name=function_name,
            variable_details=variable_details,
        )

    report = _base_report(
        title="Unhandled error type",
        problem_type=error_type,
        severity="warning",
        confidence="low",
        function_name=function_name,
        error_message=error_message,
        variable_details=variable_details,
    )
    report.explanation = (
        "Explainable does not yet have a specialized handler for this error type."
    )
    report.suspected_cause = (
        "The error type is recognized, but no detailed explanation rule exists yet."
    )
    report.suggested_next_action = (
        "Add a dedicated explainer for this error type."
    )
    report.possible_solutions = [
        "Inspect the traceback and runtime values manually.",
        "Add a dedicated handler for this error type in Explainable.",
    ]
    report.recommended_solution = (
        "Add specialized handling for this error type before relying on the report."
    )
    report.possible_risks = [
        "The current report may miss important details for this error type.",
    ]
    report.risk_level = "high"
    return report