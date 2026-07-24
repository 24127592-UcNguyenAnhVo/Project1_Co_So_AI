from constants import LYING_X, LYING_Y, SPLIT, STANDING


class State:
    def __init__(
        self,
        r,
        c,
        orient,
        bridge_states=None,
        is_split=False,
        cube2_r=None,
        cube2_c=None,
        active_cube=1,
    ):
        self.r = r
        self.c = c
        self.orient = orient

        if bridge_states is None:
            self.bridge_states = frozenset()
        elif isinstance(bridge_states, dict):
            self.bridge_states = frozenset(bridge_states.items())
        else:
            self.bridge_states = frozenset(bridge_states)

        self.is_split = is_split
        self.cube2_r = cube2_r
        self.cube2_c = cube2_c
        self.active_cube = active_cube

        normal_orientations = {STANDING, LYING_X, LYING_Y}

        if self.is_split:
            if self.orient != SPLIT:
                raise ValueError("Split state must use SPLIT orientation.")
            if self.cube2_r is None or self.cube2_c is None:
                raise ValueError("Split state requires cube2_r and cube2_c.")
            if self.active_cube not in (1, 2):
                raise ValueError("Split state requires active_cube to be 1 or 2.")
        else:
            if self.orient not in normal_orientations:
                raise ValueError(f"Invalid normal orientation: {self.orient}")
            if self.cube2_r is not None or self.cube2_c is not None:
                raise ValueError("Non-split state cannot contain cube2 position.")

    def __hash__(self):
        return hash(
            (
                self.r,
                self.c,
                self.orient,
                self.bridge_states,
                self.is_split,
                self.cube2_r,
                self.cube2_c,
                self.active_cube,
            )
        )

    def __eq__(self, other):
        if not isinstance(other, State):
            return False

        return (
            self.r,
            self.c,
            self.orient,
            self.bridge_states,
            self.is_split,
            self.cube2_r,
            self.cube2_c,
            self.active_cube,
        ) == (
            other.r,
            other.c,
            other.orient,
            other.bridge_states,
            other.is_split,
            other.cube2_r,
            other.cube2_c,
            other.active_cube,
        )

    def get_positions(self):
        if self.is_split:
            return [(self.r, self.c), (self.cube2_r, self.cube2_c)]

        if self.orient == STANDING:
            return [(self.r, self.c)]

        if self.orient == LYING_X:
            return [(self.r, self.c), (self.r, self.c + 1)]

        if self.orient == LYING_Y:
            return [(self.r, self.c), (self.r + 1, self.c)]

        raise ValueError(f"Invalid orientation: {self.orient}")

    def with_bridge_states(self, bridge_states):
        return State(
            self.r,
            self.c,
            self.orient,
            bridge_states=bridge_states,
            is_split=self.is_split,
            cube2_r=self.cube2_r,
            cube2_c=self.cube2_c,
            active_cube=self.active_cube,
        )

    def move_split_cube(self, action):
        deltas = {
            "UP": (-1, 0),
            "DOWN": (1, 0),
            "LEFT": (0, -1),
            "RIGHT": (0, 1),
        }

        if action not in deltas:
            raise ValueError(f"Invalid action: {action}")

        dr, dc = deltas[action]
        bridge_states = dict(self.bridge_states)

        if self.active_cube == 1:
            return State(
                self.r + dr,
                self.c + dc,
                SPLIT,
                bridge_states=bridge_states,
                is_split=True,
                cube2_r=self.cube2_r,
                cube2_c=self.cube2_c,
                active_cube=1,
            )

        return State(
            self.r,
            self.c,
            SPLIT,
            bridge_states=bridge_states,
            is_split=True,
            cube2_r=self.cube2_r + dr,
            cube2_c=self.cube2_c + dc,
            active_cube=2,
        )

    def switch_active_cube(self):
        if not self.is_split:
            return self

        return State(
            self.r,
            self.c,
            self.orient,
            bridge_states=dict(self.bridge_states),
            is_split=True,
            cube2_r=self.cube2_r,
            cube2_c=self.cube2_c,
            active_cube=2 if self.active_cube == 1 else 1,
        )

    def geometric_move(self, action):
        r = self.r
        c = self.c
        orient = self.orient
        bridge_states = dict(self.bridge_states)

        if self.is_split:
            return self.move_split_cube(action)

        if orient == STANDING:
            if action == "UP":
                return State(r - 2, c, LYING_Y, bridge_states)
            if action == "DOWN":
                return State(r + 1, c, LYING_Y, bridge_states)
            if action == "LEFT":
                return State(r, c - 2, LYING_X, bridge_states)
            if action == "RIGHT":
                return State(r, c + 1, LYING_X, bridge_states)

        elif orient == LYING_X:
            if action == "UP":
                return State(r - 1, c, LYING_X, bridge_states)
            if action == "DOWN":
                return State(r + 1, c, LYING_X, bridge_states)
            if action == "LEFT":
                return State(r, c - 1, STANDING, bridge_states)
            if action == "RIGHT":
                return State(r, c + 2, STANDING, bridge_states)

        elif orient == LYING_Y:
            if action == "UP":
                return State(r - 1, c, STANDING, bridge_states)
            if action == "DOWN":
                return State(r + 2, c, STANDING, bridge_states)
            if action == "LEFT":
                return State(r, c - 1, LYING_Y, bridge_states)
            if action == "RIGHT":
                return State(r, c + 1, LYING_Y, bridge_states)

        raise ValueError(f"Invalid action: {action}")
