from core.call_graph import build_call_graph


def test_build_call_graph_returns_dict():
    graph = build_call_graph("sample_target.py")
    assert isinstance(graph, dict)


def test_build_call_graph_contains_expected_edges():
    graph = build_call_graph("sample_target.py")

    assert "checkout" in graph
    assert "get_discount" in graph
    assert "calculate_discount" in graph

    assert "get_discount" in graph["checkout"]
    assert "calculate_discount" in graph["get_discount"]


def test_build_call_graph_handles_leaf_function():
    graph = build_call_graph("sample_target.py")

    assert "calculate_discount" in graph
    assert graph["calculate_discount"] == set()