import json
from pathlib import Path

from board import Board


def _normalize_switches(raw_switches):
    switches = {}

    for switch_data in raw_switches:
        if "position" not in switch_data:
            raise ValueError(
                "Every switch entry requires a 'position' field."
            )

        position = tuple(
            switch_data["position"]
        )

        switch_info = {
            key: value
            for key, value in switch_data.items()
            if key != "position"
        }

        switches[position] = switch_info

    return switches


def _normalize_split_targets(raw_split_targets):
    split_targets = {}

    for entry in raw_split_targets:
        if "position" not in entry or "targets" not in entry:
            raise ValueError(
                "Every split target entry requires 'position' and 'targets'."
            )

        position = tuple(
            entry["position"]
        )

        targets = entry["targets"]

        if len(targets) != 2:
            raise ValueError(
                f"Split switch at {position} must have exactly two targets."
            )

        split_targets[position] = (
            tuple(targets[0]),
            tuple(targets[1]),
        )

    return split_targets


def load_level(file_path):
    file_path = Path(file_path)

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if "grid" not in data:
        raise ValueError(
            f"Level file '{file_path.name}' has no 'grid' field."
        )

    raw_grid = data["grid"]

    grid = [
        list(row)
        if isinstance(row, str)
        else list(row)
        for row in raw_grid
    ]

    bridges = data.get(
        "bridges",
        {},
    )

    switches = _normalize_switches(
        data.get(
            "switches",
            [],
        )
    )

    split_targets = _normalize_split_targets(
        data.get(
            "split_targets",
            [],
        )
    )

    return Board(
        grid,
        bridges=bridges,
        switches=switches,
        split_targets=split_targets,
    )


def get_level_name(file_path):
    file_path = Path(file_path)

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data.get(
        "name",
        file_path.stem,
    )