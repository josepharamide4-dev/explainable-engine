from core.bug_chain import find_bug_chains


def test_find_bug_chains_returns_list():
    chains = find_bug_chains("sample_target.py", "calculate_discount")
    assert isinstance(chains, list)


def test_find_bug_chains_finds_expected_chain():
    chains = find_bug_chains("sample_target.py", "calculate_discount")

    assert ["checkout", "get_discount", "calculate_discount"] in chains


def test_find_bug_chains_for_unknown_function_returns_empty():
    chains = find_bug_chains("sample_target.py", "does_not_exist")
    assert chains == []