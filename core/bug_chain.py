from collections import defaultdict, deque

from core.call_graph import build_call_graph


def invert_graph(graph: dict[str, set[str]]) -> dict[str, set[str]]:
    reverse_graph = defaultdict(set)

    for caller, callees in graph.items():
        if caller not in reverse_graph:
            reverse_graph[caller] = set()

        for callee in callees:
            reverse_graph[callee].add(caller)

    return dict(reverse_graph)


def find_bug_chains(file_path: str, target_function: str) -> list[list[str]]:
    graph = build_call_graph(file_path)

    if not graph:
        return []

    reverse_graph = invert_graph(graph)

    if target_function not in reverse_graph:
        return []

    chains = []
    queue = deque([[target_function]])

    while queue:
        path = queue.popleft()
        current = path[0]
        parents = reverse_graph.get(current, set())

        if not parents:
            chains.append(path)
            continue

        extended = False
        for parent in parents:
            if parent in path:
                continue
            queue.appendleft([parent] + path)
            extended = True

        if not extended:
            chains.append(path)

    # Deduplicate while preserving order
    unique = []
    seen = set()

    for chain in chains:
        key = tuple(chain)
        if key not in seen:
            seen.add(key)
            unique.append(chain)

    return unique