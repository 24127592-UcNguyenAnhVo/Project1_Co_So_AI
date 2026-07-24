import heapq
import math
import time
import tracemalloc
from collections import deque

from constants import STANDING


def reconstruct_path(parent, goal_state):
    path = []
    current = goal_state

    while parent[current] is not None:
        previous, action = parent[current]
        path.append(action)
        current = previous

    path.reverse()
    return path


def heuristic(board, state):
    """
    Admissible heuristic for A*.

    Normal levels:
        h = max(
            ceil(minimum Manhattan distance / 2),
            orientation lower bound
        )

    Split-switch levels:
        h = 0

    The split-switch fallback is conservative because teleportation can make
    a direct Manhattan estimate overestimate the true remaining cost.
    """

    if board.is_goal(state):
        return 0.0

    if state.is_split or board.split_targets:
        return 0.0

    goal_r, goal_c = board.goal_pos

    min_distance = min(
        abs(r - goal_r) + abs(c - goal_c)
        for r, c in state.get_positions()
    )

    distance_bound = math.ceil(min_distance / 2)
    orientation_bound = 0 if state.orient == STANDING else 1

    return float(max(distance_bound, orientation_bound))


def _notify_expand(on_expand, state, expanded_nodes, frontier_size):
    if on_expand is not None:
        on_expand(
            state,
            expanded_nodes,
            frontier_size,
        )


def bfs(board, on_expand=None):
    start = board.start_state
    queue = deque([start])
    parent = {start: None}
    expanded_nodes = 0

    while queue:
        curr_state = queue.popleft()

        if board.is_goal(curr_state):
            return reconstruct_path(parent, curr_state), expanded_nodes

        expanded_nodes += 1

        for action, next_state in board.successors(curr_state):
            if next_state not in parent:
                parent[next_state] = (curr_state, action)
                queue.append(next_state)

        _notify_expand(
            on_expand,
            curr_state,
            expanded_nodes,
            len(queue),
        )

    return None, expanded_nodes


def dfs(board, on_expand=None):
    start = board.start_state
    stack = [start]
    parent = {start: None}
    expanded_nodes = 0

    while stack:
        curr_state = stack.pop()

        if board.is_goal(curr_state):
            return reconstruct_path(parent, curr_state), expanded_nodes

        expanded_nodes += 1

        for action, next_state in reversed(board.successors(curr_state)):
            if next_state not in parent:
                parent[next_state] = (curr_state, action)
                stack.append(next_state)

        _notify_expand(
            on_expand,
            curr_state,
            expanded_nodes,
            len(stack),
        )

    return None, expanded_nodes


def ucs(board, on_expand=None):
    start = board.start_state
    counter = 0
    heap = [(0.0, counter, start)]
    best_cost = {start: 0.0}
    parent = {start: None}
    expanded_nodes = 0

    while heap:
        cost, _, curr_state = heapq.heappop(heap)

        if cost > best_cost.get(curr_state, float("inf")):
            continue

        if board.is_goal(curr_state):
            return (
                reconstruct_path(parent, curr_state),
                cost,
                expanded_nodes,
            )

        expanded_nodes += 1

        for action, next_state in board.successors(curr_state):
            move_cost = board.step_cost(
                curr_state,
                action,
                next_state,
            )
            new_cost = cost + move_cost

            if new_cost < best_cost.get(next_state, float("inf")):
                best_cost[next_state] = new_cost
                parent[next_state] = (curr_state, action)
                counter += 1

                heapq.heappush(
                    heap,
                    (
                        new_cost,
                        counter,
                        next_state,
                    ),
                )

        _notify_expand(
            on_expand,
            curr_state,
            expanded_nodes,
            len(heap),
        )

    return None, None, expanded_nodes


def astar(board, on_expand=None):
    start = board.start_state
    counter = 0

    start_h = heuristic(board, start)

    heap = [(start_h, 0.0, counter, start)]
    best_cost = {start: 0.0}
    parent = {start: None}
    expanded_nodes = 0

    while heap:
        _, current_cost, _, curr_state = heapq.heappop(heap)

        if current_cost > best_cost.get(curr_state, float("inf")):
            continue

        if board.is_goal(curr_state):
            return (
                reconstruct_path(parent, curr_state),
                current_cost,
                expanded_nodes,
            )

        expanded_nodes += 1

        for action, next_state in board.successors(curr_state):
            move_cost = board.step_cost(
                curr_state,
                action,
                next_state,
            )

            new_cost = current_cost + move_cost

            if new_cost < best_cost.get(next_state, float("inf")):
                best_cost[next_state] = new_cost
                parent[next_state] = (curr_state, action)

                h = heuristic(board, next_state)
                f = new_cost + h

                counter += 1

                heapq.heappush(
                    heap,
                    (
                        f,
                        new_cost,
                        counter,
                        next_state,
                    ),
                )

        _notify_expand(
            on_expand,
            curr_state,
            expanded_nodes,
            len(heap),
        )

    return None, None, expanded_nodes


def calculate_path_cost(board, path):
    if path is None:
        return None

    state = board.start_state
    total_cost = 0.0

    for action in path:
        next_state = board.transition(
            state,
            action,
        )

        if next_state is None:
            raise ValueError(
                f"Solver returned an invalid action '{action}' for state {state!r}."
            )

        total_cost += board.step_cost(
            state,
            action,
            next_state,
        )
        state = next_state

    return total_cost


def run_search(
    board,
    algorithm,
    on_expand=None,
):
    if algorithm not in ["BFS", "DFS", "UCS", "A*"]:
        raise ValueError(
            f"Unsupported algorithm: {algorithm}"
        )

    tracemalloc.start()
    start_time = time.perf_counter()

    try:
        if algorithm == "BFS":
            path, nodes = bfs(
                board,
                on_expand=on_expand,
            )
            total_cost = None

        elif algorithm == "DFS":
            path, nodes = dfs(
                board,
                on_expand=on_expand,
            )
            total_cost = None

        elif algorithm == "UCS":
            path, total_cost, nodes = ucs(
                board,
                on_expand=on_expand,
            )

        else:
            path, total_cost, nodes = astar(
                board,
                on_expand=on_expand,
            )

        end_time = time.perf_counter()
        _, peak_mem = tracemalloc.get_traced_memory()

    finally:
        tracemalloc.stop()

    found = path is not None

    if found and algorithm in ("BFS", "DFS"):
        total_cost = calculate_path_cost(
            board,
            path,
        )

    return {
        "algorithm": algorithm,
        "found": found,
        "path": path,
        "solution_length": len(path) if found else 0,
        "total_cost": total_cost,
        "expanded_nodes": nodes,
        "time_sec": end_time - start_time,
        "peak_memory_bytes": peak_mem,
    }