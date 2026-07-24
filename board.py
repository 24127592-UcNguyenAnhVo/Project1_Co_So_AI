from constants import (
    LYING_X,
    LYING_Y,
    NORMAL_ACTIONS,
    SPLIT,
    SPLIT_ACTIONS,
    STANDING,
    VALID_MAP_CHARS,
)
from state import State


class Board:
    def __init__(self, grid, bridges=None, switches=None, split_targets=None):
        if not grid or not grid[0]:
            raise ValueError("Level cannot be empty.")

        self.rows = len(grid)
        self.cols = len(grid[0])

        for row in grid:
            if len(row) != self.cols:
                raise ValueError("All rows in the level must have the same length.")

        self.grid = [list(row) for row in grid]
        self.bridges = self._normalize_bridges(bridges or {})
        self.switches = dict(switches or {})
        self.split_targets = self._normalize_split_targets(split_targets or {})
        self._load_split_targets_from_switches()

        self.start_state = None
        self.goal_pos = None

        initial_bridge_states = {
            bridge_id: info["initial_open"]
            for bridge_id, info in self.bridges.items()
        }

        start_count = 0
        goal_count = 0

        for i in range(self.rows):
            for j in range(self.cols):
                char = self.grid[i][j]

                if char not in VALID_MAP_CHARS:
                    raise ValueError(f"Invalid character in map: '{char}'")

                if char == "S":
                    start_count += 1
                    self.start_state = State(
                        i,
                        j,
                        STANDING,
                        bridge_states=initial_bridge_states,
                    )
                    self.grid[i][j] = "1"

                elif char == "G":
                    goal_count += 1
                    self.goal_pos = (i, j)
                    self.grid[i][j] = "1"

        if start_count != 1:
            raise ValueError("Level must contain exactly one start tile.")

        if goal_count != 1:
            raise ValueError("Level must contain exactly one goal tile.")

        self._validate_metadata()

    def _normalize_bridges(self, bridges):
        normalized = {}

        for bridge_id, info in bridges.items():
            cells = info.get("cells", [])

            normalized[bridge_id] = {
                **info,
                "cells": {tuple(cell) for cell in cells},
                "initial_open": info.get("initial_open", False),
            }

        return normalized

    def _normalize_split_targets(self, split_targets):
        normalized = {}

        for position, targets in split_targets.items():
            normalized_position = tuple(position)

            if len(targets) != 2:
                raise ValueError(
                    f"Split switch at {normalized_position} must have exactly two targets."
                )

            normalized[normalized_position] = (
                tuple(targets[0]),
                tuple(targets[1]),
            )

        return normalized

    def _load_split_targets_from_switches(self):
        for position, switch in self.switches.items():
            if switch.get("type") != "split":
                continue

            if "targets" not in switch:
                raise ValueError(f"Split switch at {position} requires targets.")

            normalized_position = tuple(position)
            targets = switch["targets"]

            if len(targets) != 2:
                raise ValueError(
                    f"Split switch at {normalized_position} must have exactly two targets."
                )

            normalized_targets = (
                tuple(targets[0]),
                tuple(targets[1]),
            )

            if (
                normalized_position in self.split_targets
                and self.split_targets[normalized_position] != normalized_targets
            ):
                raise ValueError(
                    f"Conflicting split targets for switch at {normalized_position}."
                )

            self.split_targets[normalized_position] = normalized_targets

    def _validate_metadata(self):
        self._validate_bridges()

        expected_switch_tiles = {
            "soft": "O",
            "heavy": "X",
            "split": "T",
        }

        valid_behaviors = {
            "toggle",
            "open",
            "close",
        }

        for position, switch in self.switches.items():
            position = tuple(position)

            if not self.is_inside_board([position]):
                raise ValueError(f"Switch position outside board: {position}")

            switch_type = switch.get("type", "soft")

            if switch_type not in expected_switch_tiles:
                raise ValueError(f"Invalid switch type: {switch_type}")

            behavior = switch.get("behavior", "toggle")

            if behavior not in valid_behaviors:
                raise ValueError(
                    f"Invalid switch behavior '{behavior}' at {position}."
                )

            r, c = position
            expected_tile = expected_switch_tiles[switch_type]

            if self.grid[r][c] != expected_tile:
                raise ValueError(
                    f"{switch_type} switch at {position} "
                    f"must be on '{expected_tile}' tile."
                )

            for bridge_id in switch.get("bridges", []):
                if bridge_id not in self.bridges:
                    raise ValueError(
                        f"Switch at {position} references unknown bridge: {bridge_id}"
                    )

        for position, targets in self.split_targets.items():
            if not self.is_inside_board([position]):
                raise ValueError(f"Split switch position outside board: {position}")

            r, c = position

            if self.grid[r][c] != "T":
                raise ValueError(f"Split target at {position} must be on 'T' tile.")

            if len(targets) != 2:
                raise ValueError(
                    f"Split switch at {position} must have exactly two targets."
                )

            cube1, cube2 = targets

            if cube1 == cube2:
                raise ValueError(f"Split targets at {position} must be different.")

            for target in (cube1, cube2):
                if len(target) != 2:
                    raise ValueError(f"Invalid split target coordinate: {target}")

                if not self.is_inside_board([target]):
                    raise ValueError(f"Split target outside board: {target}")

                target_r, target_c = target

                if self.grid[target_r][target_c] == "0":
                    raise ValueError(f"Split target cannot be on void: {target}")

        # Fail fast when a special tile exists without the metadata required
        # to make it behave as the tile shown on the board.
        for r in range(self.rows):
            for c in range(self.cols):
                position = (r, c)
                tile = self.grid[r][c]

                if tile == "O":
                    switch = self.switches.get(position)

                    if switch is None:
                        raise ValueError(
                            f"Soft switch tile at {position} has no switch metadata."
                        )

                    if switch.get("type", "soft") != "soft":
                        raise ValueError(
                            f"Tile 'O' at {position} must be configured as a soft switch."
                        )

                elif tile == "X":
                    switch = self.switches.get(position)

                    if switch is None:
                        raise ValueError(
                            f"Heavy switch tile at {position} has no switch metadata."
                        )

                    if switch.get("type") != "heavy":
                        raise ValueError(
                            f"Tile 'X' at {position} must be configured as a heavy switch."
                        )

                elif tile == "T":
                    if position not in self.split_targets:
                        raise ValueError(
                            f"Split switch tile at {position} has no split targets."
                        )

    def _validate_bridges(self):
        used_bridge_cells = set()

        for bridge_id, info in self.bridges.items():
            if not isinstance(info["initial_open"], bool):
                raise ValueError(
                    f"Bridge {bridge_id} initial_open must be a boolean."
                )

            for cell in info["cells"]:
                if len(cell) != 2:
                    raise ValueError(
                        f"Invalid bridge coordinate for {bridge_id}: {cell}"
                    )

                if not self.is_inside_board([cell]):
                    raise ValueError(
                        f"Bridge {bridge_id} cell outside board: {cell}"
                    )

                r, c = cell

                if self.grid[r][c] != "B":
                    raise ValueError(
                        f"Bridge {bridge_id} cell {cell} must be on 'B' tile."
                    )

                if cell in used_bridge_cells:
                    raise ValueError(
                        f"Bridge cell belongs to multiple bridges: {cell}"
                    )

                used_bridge_cells.add(cell)

        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == "B" and (r, c) not in used_bridge_cells:
                    raise ValueError(
                        f"Bridge tile at {(r, c)} does not belong to any bridge."
                    )

    def is_inside_board(self, positions):
        return all(
            0 <= r < self.rows and 0 <= c < self.cols
            for r, c in positions
        )

    def get_bridge_at(self, position):
        for bridge_id, info in self.bridges.items():
            if position in info["cells"]:
                return bridge_id

        return None

    def is_supported(self, positions, state=None):
        bridge_states = dict(state.bridge_states) if state else {}

        for r, c in positions:
            if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
                return False

            if self.grid[r][c] == "0":
                return False

            bridge_id = self.get_bridge_at((r, c))

            if (
                bridge_id is not None
                and not bridge_states.get(bridge_id, False)
            ):
                return False

        return True

    def breaks_fragile(self, state):
        if state.is_split or state.orient != STANDING:
            return False

        return self.grid[state.r][state.c] == "F"

    def touches_fragile(self, state):
        return any(
            self.grid[r][c] == "F"
            for r, c in state.get_positions()
        )

    def fragile_positions(self, state):
        return {
            (r, c)
            for r, c in state.get_positions()
            if self.grid[r][c] == "F"
        }

    def get_pressed_switches(self, state, positions=None):
        pressed = []
        check_positions = (
            positions
            if positions is not None
            else state.get_positions()
        )

        for position in check_positions:
            switch = self.switches.get(position)

            if switch is not None:
                pressed.append((position, switch))

        return pressed

    def can_activate_heavy_switch(self, state, switch_position):
        return (
            not state.is_split
            and state.orient == STANDING
            and (state.r, state.c) == switch_position
        )

    def is_switch_active(self, state, position, switch):
        switch_type = switch.get("type", "soft")

        if switch_type == "soft":
            return position in state.get_positions()

        if switch_type == "heavy":
            return self.can_activate_heavy_switch(
                state,
                position,
            )

        if switch_type == "split":
            return (
                not state.is_split
                and state.orient == STANDING
                and (state.r, state.c) == position
            )

        return False

    def update_bridges(self, state, switch):
        bridge_states = dict(state.bridge_states)
        behavior = switch.get("behavior", "toggle")

        for bridge_id in switch.get("bridges", []):
            if behavior == "toggle":
                bridge_states[bridge_id] = not bridge_states.get(
                    bridge_id,
                    False,
                )
            elif behavior == "open":
                bridge_states[bridge_id] = True
            elif behavior == "close":
                bridge_states[bridge_id] = False
            else:
                # This should already be prevented by metadata validation.
                raise ValueError(f"Invalid switch behavior: {behavior}")

        return state.with_bridge_states(bridge_states)

    def apply_switches(self, old_state, new_state):
        current_state = new_state

        for position, switch in self.switches.items():
            position = tuple(position)
            was_active = self.is_switch_active(
                old_state,
                position,
                switch,
            )
            is_active = self.is_switch_active(
                new_state,
                position,
                switch,
            )

            if not was_active and is_active:
                current_state = self.update_bridges(
                    current_state,
                    switch,
                )

        return current_state

    def activates_switch(self, old_state, new_state):
        for position, switch in self.switches.items():
            position = tuple(position)
            was_active = self.is_switch_active(
                old_state,
                position,
                switch,
            )
            is_active = self.is_switch_active(
                new_state,
                position,
                switch,
            )

            if not was_active and is_active:
                return True

        return False

    def apply_split_switch(self, state):
        if state.is_split or state.orient != STANDING:
            return state

        position = (state.r, state.c)

        if position not in self.split_targets:
            return state

        cube1, cube2 = self.split_targets[position]

        return State(
            cube1[0],
            cube1[1],
            SPLIT,
            bridge_states=dict(state.bridge_states),
            is_split=True,
            cube2_r=cube2[0],
            cube2_c=cube2[1],
            active_cube=1,
        )

    def split_cubes_overlap(self, state):
        if not state.is_split:
            return False

        return (
            state.r == state.cube2_r
            and state.c == state.cube2_c
        )

    def try_merge(self, state):
        if not state.is_split:
            return state

        r1, c1 = state.r, state.c
        r2, c2 = state.cube2_r, state.cube2_c

        if abs(r1 - r2) + abs(c1 - c2) != 1:
            return state

        bridge_states = dict(state.bridge_states)

        if r1 == r2:
            return State(
                r1,
                min(c1, c2),
                LYING_X,
                bridge_states=bridge_states,
            )

        return State(
            min(r1, r2),
            c1,
            LYING_Y,
            bridge_states=bridge_states,
        )

    def step_cost(self, old_state, action, new_state):
        cost = 0.5 if action == "SWITCH_CUBE" else 1.0

        if action == "SWITCH_CUBE":
            return cost

        if self.activates_switch(old_state, new_state):
            cost += 0.2

        newly_touched_fragile = (
            self.fragile_positions(new_state)
            - self.fragile_positions(old_state)
        )

        if newly_touched_fragile:
            cost += 0.5

        if not old_state.is_split and new_state.is_split:
            cost += 1.0

        return cost

    def transition(self, state, action):
        if action == "SWITCH_CUBE":
            if not state.is_split:
                return None

            return state.switch_active_cube()

        next_state = state.geometric_move(action)

        if self.split_cubes_overlap(next_state):
            return None

        positions = next_state.get_positions()

        if not self.is_inside_board(positions):
            return None

        if not self.is_supported(positions, next_state):
            return None

        if self.breaks_fragile(next_state):
            return None

        next_state = self.apply_switches(
            state,
            next_state,
        )

        if not self.is_supported(
            next_state.get_positions(),
            next_state,
        ):
            return None

        before_split = next_state
        next_state = self.apply_split_switch(next_state)

        # Teleported split cubes can land directly on soft switches.
        # A single cube is allowed to activate a soft switch, so process
        # newly pressed switches at the teleport destinations as well.
        if not before_split.is_split and next_state.is_split:
            next_state = self.apply_switches(
                before_split,
                next_state,
            )

        if not self.is_supported(
            next_state.get_positions(),
            next_state,
        ):
            return None

        next_state = self.try_merge(next_state)

        return next_state

    def successors(self, state):
        actions = (
            SPLIT_ACTIONS
            if state.is_split
            else NORMAL_ACTIONS
        )
        valid_moves = []

        for action in actions:
            next_state = self.transition(
                state,
                action,
            )

            if next_state is not None:
                valid_moves.append(
                    (action, next_state)
                )

        return valid_moves

    def is_goal(self, state):
        if state.is_split:
            return False

        return (
            state.orient == STANDING
            and (state.r, state.c) == self.goal_pos
        )
