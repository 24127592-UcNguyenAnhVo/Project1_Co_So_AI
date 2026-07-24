from algorithms import astar, heuristic, run_search, ucs
from board import Board
from constants import LYING_X, LYING_Y, SPLIT, STANDING
from level_loader import load_level
from state import State

def run_unit_tests():
    print("========== UNIT TEST CHECKLIST (ASSERTIONS) ==========")

    s1 = State(1, 1, STANDING, bridge_states={"b1": True})
    s2 = State(1, 1, STANDING, bridge_states={"b1": True})
    s3 = State(1, 1, STANDING, bridge_states={"b1": False})
    s4 = State(1, 1, STANDING, bridge_states=frozenset({("b1", True)}))
    assert s1 == s2
    assert hash(s1) == hash(s2)
    assert s1 != s3
    assert s1 == s4

    stand = State(1, 1, STANDING)
    assert stand.geometric_move("UP") == State(-1, 1, LYING_Y)
    assert stand.geometric_move("DOWN") == State(2, 1, LYING_Y)
    assert stand.geometric_move("LEFT") == State(1, -1, LYING_X)
    assert stand.geometric_move("RIGHT") == State(1, 2, LYING_X)

    hx = State(1, 1, LYING_X)
    assert hx.geometric_move("UP") == State(0, 1, LYING_X)
    assert hx.geometric_move("DOWN") == State(2, 1, LYING_X)
    assert hx.geometric_move("LEFT") == State(1, 0, STANDING)
    assert hx.geometric_move("RIGHT") == State(1, 3, STANDING)

    hy = State(1, 1, LYING_Y)
    assert hy.geometric_move("UP") == State(0, 1, STANDING)
    assert hy.geometric_move("DOWN") == State(3, 1, STANDING)
    assert hy.geometric_move("LEFT") == State(1, 0, LYING_Y)
    assert hy.geometric_move("RIGHT") == State(1, 2, LYING_Y)

    try:
        stand.geometric_move("ABC")
        assert False
    except ValueError:
        pass

    try:
        State(1, 1, STANDING, is_split=True)
        assert False
    except ValueError:
        pass
    
    try:
        State(1, 1, SPLIT)
        assert False
    except ValueError:
        pass

    try:
        State(
            1,
            1,
            STANDING,
            is_split=True,
            cube2_r=2,
            cube2_c=2,
        )
        assert False
    except ValueError:
        pass

    split_state = State(1, 1, SPLIT, is_split=True, cube2_r=2, cube2_c=2, active_cube=1)
    assert split_state.geometric_move("UP") == State(
        0, 1, SPLIT, is_split=True, cube2_r=2, cube2_c=2, active_cube=1
    )
    assert split_state.switch_active_cube().active_cube == 2

    test_grid = [
        ["1", "1", "1", "1", "0"],
        ["1", "S", "1", "1", "1"],
        ["1", "1", "1", "0", "G"],
        ["0", "1", "1", "1", "1"],
    ]
    board = Board(test_grid)

    out_state = State(-1, 0, STANDING)
    assert not board.is_inside_board(out_state.get_positions())

    void_state = State(0, 4, STANDING)
    assert not board.is_supported(void_state.get_positions(), void_state)

    win_state = State(2, 4, STANDING)
    assert board.is_goal(win_state)

    lying_goal = State(2, 3, LYING_X)
    assert not board.is_goal(lying_goal)

    fragile_board = Board(
        [
            ["1", "1", "1", "1"],
            ["1", "S", "F", "1"],
            ["1", "1", "G", "1"],
        ]
    )
    assert fragile_board.breaks_fragile(State(1, 2, STANDING))
    assert not fragile_board.breaks_fragile(State(1, 1, LYING_X))
    assert not fragile_board.breaks_fragile(State(0, 2, LYING_Y))
    assert fragile_board.transition(State(1, 3, LYING_X), "LEFT") is None

    bridge_board = Board(
        [["S", "B", "G"]],
        bridges={"b1": {"cells": [(0, 1)], "initial_open": False}},
    )
    closed_bridge = State(0, 1, STANDING, bridge_states={"b1": False})
    open_bridge = State(0, 1, STANDING, bridge_states={"b1": True})
    assert not bridge_board.is_supported(closed_bridge.get_positions(), closed_bridge)
    assert bridge_board.is_supported(open_bridge.get_positions(), open_bridge)

    invalid_bridge_cases = [
        {
            "bridges": {"b1": {"cells": [(0, 1)], "initial_open": "False"}},
        },
        {
            "bridges": {"b1": {"cells": [(0, 3)], "initial_open": False}},
        },
        {
            "grid": [["S", "1", "G"]],
            "bridges": {"b1": {"cells": [(0, 1)], "initial_open": False}},
        },
        {
            "bridges": {
                "b1": {"cells": [(0, 1)], "initial_open": False},
                "b2": {"cells": [(0, 1)], "initial_open": True},
            },
        },
    ]
    for case in invalid_bridge_cases:
        try:
            Board(
                case.get("grid", [["S", "B", "G"]]),
                bridges=case["bridges"],
            )
            assert False
        except ValueError:
            pass

    switch_board = Board(
        [["1", "S", "O", "B", "G"]],
        bridges={"b1": {"cells": [(0, 3)], "initial_open": False}},
        switches={(0, 2): {"type": "soft", "behavior": "toggle", "bridges": ["b1"]}},
    )
    before_switch = State(0, 1, STANDING, bridge_states={"b1": False})
    on_switch = State(0, 2, STANDING, bridge_states={"b1": False})
    toggled = switch_board.apply_switches(before_switch, on_switch)
    assert dict(toggled.bridge_states)["b1"] is True
    assert dict(switch_board.apply_switches(on_switch, toggled).bridge_states)["b1"] is True

    soft_lie_x = State(0, 2, LYING_X, bridge_states={"b1": False})
    assert dict(switch_board.apply_switches(before_switch, soft_lie_x).bridge_states)["b1"] is True

    vertical_switch_board = Board(
        [
            ["1", "S", "1"],
            ["1", "O", "1"],
            ["1", "B", "G"],
        ],
        bridges={"b1": {"cells": [(2, 1)], "initial_open": False}},
        switches={(1, 1): {"type": "soft", "behavior": "toggle", "bridges": ["b1"]}},
    )
    soft_lie_y = State(1, 1, LYING_Y, bridge_states={"b1": False})
    assert dict(vertical_switch_board.apply_switches(before_switch, soft_lie_y).bridge_states)["b1"] is True

    soft_split = State(0, 2, SPLIT, bridge_states={"b1": False}, is_split=True, cube2_r=0, cube2_c=4)
    assert dict(switch_board.apply_switches(before_switch, soft_split).bridge_states)["b1"] is True

    heavy_board = Board(
        [["1", "S", "X", "B", "G"]],
        bridges={"b1": {"cells": [(0, 3)], "initial_open": False}},
        switches={(0, 2): {"type": "heavy", "behavior": "open", "bridges": ["b1"]}},
    )
    assert dict(heavy_board.apply_switches(before_switch, on_switch).bridge_states)["b1"] is True
    assert dict(heavy_board.apply_switches(before_switch, soft_lie_x).bridge_states)["b1"] is False
    assert dict(heavy_board.apply_switches(before_switch, soft_split).bridge_states)["b1"] is False
    assert heavy_board.step_cost(before_switch, "RIGHT", soft_lie_x) == 1.0

    heavy_from_lying = heavy_board.apply_switches(
        State(0, 1, LYING_X, bridge_states={"b1": False}),
        State(0, 2, STANDING, bridge_states={"b1": False}),
    )
    assert dict(heavy_from_lying.bridge_states)["b1"] is True

    open_switch = {"type": "soft", "behavior": "open", "bridges": ["b1"]}
    close_switch = {"type": "soft", "behavior": "close", "bridges": ["b1"]}
    assert dict(switch_board.update_bridges(closed_bridge, open_switch).bridge_states)["b1"] is True
    assert dict(switch_board.update_bridges(open_bridge, open_switch).bridge_states)["b1"] is True
    assert dict(switch_board.update_bridges(open_bridge, close_switch).bridge_states)["b1"] is False
    assert dict(switch_board.update_bridges(closed_bridge, close_switch).bridge_states)["b1"] is False

    try:
        Board(
            [["1", "S", "O", "B", "G"]],
            bridges={"b1": {"cells": [(0, 3)], "initial_open": False}},
            switches={(0, 2): {"type": "soft", "behavior": "toggle", "bridges": ["unknown"]}},
        )
        assert False
    except ValueError:
        pass

    bridge_closes_under_block = Board(
        [["S", "O", "B", "G"]],
        bridges={"b1": {"cells": [(0, 2)], "initial_open": True}},
        switches={(0, 1): {"type": "soft", "behavior": "toggle", "bridges": ["b1"]}},
    )
    assert bridge_closes_under_block.transition(
        State(0, 0, STANDING, bridge_states={"b1": True}),
        "RIGHT",
    ) is None

    split_board = Board(
        [
            ["1", "1", "1"],
            ["1", "S", "T"],
            ["1", "1", "G"],
        ],
        split_targets={(1, 2): ((0, 0), (2, 2))},
    )
    split_result = split_board.apply_split_switch(State(1, 2, STANDING))
    assert split_result.is_split
    assert split_result.get_positions() == [(0, 0), (2, 2)]
    assert split_result.active_cube == 1
    assert not split_board.apply_split_switch(State(1, 1, LYING_X)).is_split

    moved_split = split_result.geometric_move("RIGHT")
    assert moved_split.get_positions() == [(0, 1), (2, 2)]
    assert moved_split.switch_active_cube().geometric_move("LEFT").get_positions() == [(0, 1), (2, 1)]
    assert split_board.transition(State(0, 0, SPLIT, is_split=True, cube2_r=2, cube2_c=2), "UP") is None

    assert split_board.try_merge(State(1, 0, SPLIT, is_split=True, cube2_r=1, cube2_c=1)) == State(1, 0, LYING_X)
    assert split_board.try_merge(State(0, 1, SPLIT, is_split=True, cube2_r=1, cube2_c=1)) == State(0, 1, LYING_Y)
    assert split_board.try_merge(split_result).is_split

    overlap_board = Board(
        [
            ["1", "1", "1"],
            ["S", "1", "G"],
            ["1", "1", "1"],
        ]
    )

    overlap_state = State(
        1,
        0,
        SPLIT,
        is_split=True,
        cube2_r=1,
        cube2_c=1,
        active_cube=1,
    )

    assert overlap_board.transition(
        overlap_state,
        "RIGHT",
    ) is None

    split_metadata_board = Board(
        [
            ["1", "1", "1"],
            ["1", "S", "T"],
            ["1", "1", "G"],
        ],
        switches={(1, 2): {"type": "split", "targets": ((0, 0), (2, 2))}},
    )
    assert split_metadata_board.apply_split_switch(State(1, 2, STANDING)).is_split

    invalid_split_cases = [
        {"split_targets": {(1, 2): ((0, 0), (3, 3))}},
        {"split_targets": {(1, 2): ((0, 0), (0, 0))}},
        {
            "grid": [
                ["1", "1", "1"],
                ["1", "S", "T"],
                ["1", "0", "G"],
            ],
            "split_targets": {(1, 2): ((0, 0), (2, 1))},
        },
    ]
    for case in invalid_split_cases:
        try:
            Board(
                case.get(
                    "grid",
                    [
                        ["1", "1", "1"],
                        ["1", "S", "T"],
                        ["1", "1", "G"],
                    ],
                ),
                bridges=case.get("bridges"),
                split_targets=case["split_targets"],
            )
            assert False
        except ValueError:
            pass

    split_to_closed_bridge = Board(
        [
            ["1", "1", "1"],
            ["S", "1", "T"],
            ["1", "B", "G"],
        ],
        bridges={"b1": {"cells": [(2, 1)], "initial_open": False}},
        split_targets={(1, 2): ((0, 0), (2, 1))},
    )
    assert split_to_closed_bridge.transition(
        State(1, 0, LYING_X, bridge_states={"b1": False}),
        "RIGHT",
    ) is None

    invalid_switch_metadata = [
        ({"type": "soft", "behavior": "toggle", "bridges": ["b1"]}, "X"),
        ({"type": "heavy", "behavior": "toggle", "bridges": ["b1"]}, "O"),
        ({"type": "split", "targets": ((0, 0), (2, 2))}, "O"),
    ]
    for switch, tile in invalid_switch_metadata:
        try:
            Board(
                [
                    ["1", "1", "1"],
                    ["1", "S", tile],
                    ["1", "1", "G"],
                ],
                bridges={"b1": {"cells": [], "initial_open": False}},
                switches={(1, 2): switch},
            )
            assert False
        except ValueError:
            pass


    # JSON-loaded bridge coordinates are lists; Board must normalize them to tuples.
    json_style_bridge_board = Board(
        [["S", "B", "G"]],
        bridges={
            "b1": {
                "cells": [[0, 1]],
                "initial_open": True,
            }
        },
    )
    assert json_style_bridge_board.get_bridge_at((0, 1)) == "b1"

    # Every B tile must belong to exactly one configured bridge.
    try:
        Board([["S", "B", "G"]])
        assert False
    except ValueError:
        pass

    # O, X and T tiles cannot silently behave like normal floor when metadata is missing.
    for invalid_grid in (
        [["S", "O", "G"]],
        [["S", "X", "G"]],
        [["S", "T", "G"]],
    ):
        try:
            Board(invalid_grid)
            assert False
        except ValueError:
            pass

    # Invalid switch behavior must be rejected while loading the level.
    try:
        Board(
            [["S", "O", "B", "G"]],
            bridges={
                "b1": {
                    "cells": [(0, 2)],
                    "initial_open": False,
                }
            },
            switches={
                (0, 1): {
                    "type": "soft",
                    "behavior": "INVALID",
                    "bridges": ["b1"],
                }
            },
        )
        assert False
    except ValueError:
        pass

    # Split switch can also activate its linked bridge before the block is split.
    split_bridge_board = Board(
        [
            ["1", "1", "1"],
            ["S", "T", "G"],
            ["1", "B", "1"],
        ],
        bridges={
            "b1": {
                "cells": [[2, 1]],
                "initial_open": False,
            }
        },
        switches={
            (1, 1): {
                "type": "split",
                "targets": [[0, 0], [2, 2]],
                "behavior": "toggle",
                "bridges": ["b1"],
            }
        },
    )
    split_before = State(
        1,
        0,
        STANDING,
        bridge_states={"b1": False},
    )
    split_pressed = State(
        1,
        1,
        STANDING,
        bridge_states={"b1": False},
    )
    split_toggled = split_bridge_board.apply_switches(
        split_before,
        split_pressed,
    )
    assert dict(split_toggled.bridge_states)["b1"] is True

    # A cube teleported by a split switch must activate a soft switch
    # immediately when it lands on that switch.
    split_to_soft_board = Board(
        [
            ["1", "O", "1", "1", "1"],
            ["S", "1", "T", "G", "1"],
            ["1", "1", "B", "1", "1"],
        ],
        bridges={
            "b1": {
                "cells": [(2, 2)],
                "initial_open": False,
            }
        },
        switches={
            (1, 2): {
                "type": "split",
                "targets": ((0, 0), (0, 1)),
            },
            (0, 1): {
                "type": "soft",
                "behavior": "toggle",
                "bridges": ["b1"],
            },
        },
    )
    split_to_soft_start = State(
        1,
        0,
        LYING_X,
        bridge_states={"b1": False},
    )
    split_to_soft_result = split_to_soft_board.transition(
        split_to_soft_start,
        "RIGHT",
    )
    assert split_to_soft_result is not None
    assert dict(split_to_soft_result.bridge_states)["b1"] is True

    fragile_split_board = Board(
        [
            ["S", "F", "G"],
            ["1", "1", "1"],
        ]
    )
    fragile_split_state = State(
        1,
        0,
        SPLIT,
        is_split=True,
        cube2_r=0,
        cube2_c=1,
        active_cube=1,
    )
    switched_cube_state = fragile_split_state.switch_active_cube()
    assert (
        fragile_split_board.step_cost(
            fragile_split_state,
            "SWITCH_CUBE",
            switched_cube_state,
        )
        == 0.5
    )

    moved_active_cube = fragile_split_state.geometric_move("RIGHT")
    assert (
        fragile_split_board.step_cost(
            fragile_split_state,
            "RIGHT",
            moved_active_cube,
        )
        == 1.0
    )
    heuristic_board = Board(
        [
            ["1", "1", "1", "1", "1"],
            ["1", "S", "1", "G", "1"],
            ["1", "1", "1", "1", "1"],
        ]
    )

    assert heuristic(
        heuristic_board,
        heuristic_board.start_state,
    ) >= 0

    heuristic_goal_state = State(
        heuristic_board.goal_pos[0],
        heuristic_board.goal_pos[1],
        STANDING,
    )

    assert heuristic(
        heuristic_board,
        heuristic_goal_state,
    ) == 0.0
    print("All assertions passed!\n")

def check_ucs_astar(board, test_name):
    ucs_result = run_search(board, "UCS")
    astar_result = run_search(board, "A*")

    assert ucs_result["found"] == astar_result["found"]

    if ucs_result["found"]:
        assert abs(
            ucs_result["total_cost"]
            - astar_result["total_cost"]
        ) < 1e-9

        replay_state = board.start_state

        for action in astar_result["path"]:
            replay_state = board.transition(
                replay_state,
                action,
            )

            assert replay_state is not None

        assert board.is_goal(replay_state)

    print(
        f"{test_name}: "
        f"UCS cost={ucs_result['total_cost']}, "
        f"A* cost={astar_result['total_cost']}, "
        f"UCS expanded={ucs_result['expanded_nodes']}, "
        f"A* expanded={astar_result['expanded_nodes']}"
    )

    return astar_result

def run_astar_advanced_tests():
    print("========== A* ADVANCED TESTS ==========")

    #Chỗ chèn test advanced
    fragile_astar_board = Board(
        [
            list("SF1G"),
        ]
    )

    fragile_result = check_ucs_astar(
        fragile_astar_board,
        "Fragile",
    )

    assert fragile_result["found"] is True

    soft_astar_board = Board(
        [
            list("SO11B1G"),
        ],
        bridges={
            "b1": {
                "cells": [[0, 4]],
                "initial_open": False,
            }
        },
        switches={
            (0, 1): {
                "type": "soft",
                "behavior": "open",
                "bridges": ["b1"],
            }
        },
    )

    soft_result = check_ucs_astar(
        soft_astar_board,
        "Soft Switch + Bridge",
    )

    assert soft_result["found"] is True

    heavy_astar_board = Board(
        [
            list("S11XB1G"),
        ],
        bridges={
            "b1": {
                "cells": [[0, 4]],
                "initial_open": False,
            }
        },
        switches={
            (0, 3): {
                "type": "heavy",
                "behavior": "open",
                "bridges": ["b1"],
            }
        },
    )

    heavy_result = check_ucs_astar(
        heavy_astar_board,
        "Heavy Switch + Bridge",
    )

    assert heavy_result["found"] is True

    combined_astar_board = Board(
        [
            list("SOF1B1G"),
        ],
        bridges={
            "b1": {
                "cells": [[0, 4]],
                "initial_open": False,
            }
        },
        switches={
            (0, 1): {
                "type": "soft",
                "behavior": "open",
                "bridges": ["b1"],
            }
        },
    )

    combined_result = check_ucs_astar(
        combined_astar_board,
        "Fragile + Soft + Bridge",
    )

    assert combined_result["found"] is True

    split_astar_board = Board(
        [
            list("0000000"),
            list("0000111"),
            list("S11T11G"),
            list("0000111"),
            list("0000000"),
        ],
        split_targets={
            (2, 3): (
                (1, 4),
                (3, 4),
            )
        },
    )

    split_result = check_ucs_astar(
        split_astar_board,
        "Split Switch",
    )

    assert split_result["found"] is True
    assert "SWITCH_CUBE" in split_result["path"]

    print("All A* advanced tests passed!\n")

def run_level_loader_tests():
    print("========== LEVEL LOADER TESTS ==========")

    basic_board = load_level(
        "levels/level_01.json"
    )

    basic_result = run_search(
        basic_board,
        "A*",
    )

    assert basic_result["found"] is True

    soft_board = load_level(
        "levels/level_02.json"
    )

    soft_result = run_search(
        soft_board,
        "A*",
    )

    assert soft_result["found"] is True

    print("All level loader tests passed!\n")


def run_solvers_demo():
    print("================ SEARCH DEMO ================")

    solvable_map = [
        ["1", "1", "1", "1", "1", "1"],
        ["1", "S", "1", "1", "1", "1"],
        ["1", "1", "1", "1", "G", "1"],
        ["1", "1", "1", "1", "1", "1"],
    ]

    unsolvable_map = [
        ["S", "1", "1", "1"],
        ["0", "1", "0", "1"],
        ["0", "1", "1", "G"],
    ]

    print("--- Solvable Map ---")
    board_sol = Board(solvable_map)
    res_bfs_sol = run_search(board_sol, "BFS")
    print(
        f"BFS Found: {res_bfs_sol['found']}, Path length: {res_bfs_sol['solution_length']}, "
        f"Time: {res_bfs_sol['time_sec']:.6f}s"
    )
    assert res_bfs_sol["found"] is True

    res_ucs_sol = run_search(board_sol, "UCS")
    print(
        f"UCS Found: {res_ucs_sol['found']}, Cost: {res_ucs_sol['total_cost']}, "
        f"Time: {res_ucs_sol['time_sec']:.6f}s"
    )
    assert res_ucs_sol["found"] is True
    assert isinstance(res_ucs_sol["total_cost"], float)

    res_astar_sol = run_search(board_sol, "A*")

    print(
        f"A* Found: {res_astar_sol['found']}, "
        f"Cost: {res_astar_sol['total_cost']}, "
        f"Expanded: {res_astar_sol['expanded_nodes']}, "
        f"Time: {res_astar_sol['time_sec']:.6f}s"
    )

    assert res_astar_sol["found"] is True

    assert abs(
        res_astar_sol["total_cost"]
        - res_ucs_sol["total_cost"]
    ) < 1e-9

    replay_state = board_sol.start_state

    for action in res_astar_sol["path"]:
        replay_state = board_sol.transition(
            replay_state,
            action,
        )

        assert replay_state is not None

    assert board_sol.is_goal(replay_state)

    print("\n--- Unsolvable Map ---")
    board_unsol = Board(unsolvable_map)
    res_bfs_unsol = run_search(board_unsol, "BFS")
    print(
        f"BFS Found: {res_bfs_unsol['found']}, Path length: {res_bfs_unsol['solution_length']}, "
        f"Time: {res_bfs_unsol['time_sec']:.6f}s"
    )
    assert res_bfs_unsol["found"] is False

    res_ucs_unsol = run_search(board_unsol, "UCS")
    assert res_ucs_unsol["found"] is False
    assert res_ucs_unsol["total_cost"] is None

    class WeightedGraphBoard:
        start_state = "S"

        def is_goal(self, state):
            return state == "G"

        def successors(self, state):
            graph = {
                "S": [("FAST_EXPENSIVE", "G"), ("SLOW_1", "A")],
                "A": [("SLOW_2", "B")],
                "B": [("SLOW_3", "G")],
                "G": [],
            }
            return graph[state]

        def step_cost(self, old_state, action, new_state):
            costs = {
                "FAST_EXPENSIVE": 5.0,
                "SLOW_1": 1.0,
                "SLOW_2": 1.0,
                "SLOW_3": 1.0,
            }
            return costs[action]

    ucs_path, ucs_cost, _ = ucs(WeightedGraphBoard())
    assert ucs_path == ["SLOW_1", "SLOW_2", "SLOW_3"]
    assert ucs_cost == 3.0

    res_astar_unsol = run_search(board_unsol,"A*",)

    assert res_astar_unsol["found"] is False
    assert res_astar_unsol["total_cost"] is None


if __name__ == "__main__":
    run_unit_tests()
    run_astar_advanced_tests()
    run_level_loader_tests()
    run_solvers_demo()