import csv
import gc
import statistics
from pathlib import Path

from algorithms import run_search
from level_loader import get_level_name, load_level


BASE_DIR = Path(__file__).resolve().parent
LEVELS_DIR = BASE_DIR / "levels"
RESULTS_DIR = BASE_DIR / "results"

ALGORITHMS = [
    "BFS",
    "DFS",
    "UCS",
    "A*",
]

RUNS_PER_CASE = 5


def discover_levels():
    return sorted(
        LEVELS_DIR.glob("*.json"),
        key=lambda path: path.name.lower(),
    )


def run_benchmark():
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    levels = discover_levels()

    if not levels:
        raise RuntimeError(
            "No JSON levels found in the levels directory."
        )

    rows = []

    total_cases = (
        len(levels)
        * len(ALGORITHMS)
        * RUNS_PER_CASE
    )

    case_index = 0

    for level_path in levels:
        level_name = get_level_name(
            level_path
        )

        for algorithm in ALGORITHMS:
            for run_number in range(
                1,
                RUNS_PER_CASE + 1,
            ):
                case_index += 1

                gc.collect()

                board = load_level(
                    level_path
                )

                result = run_search(
                    board,
                    algorithm,
                    on_expand=None,
                )

                row = {
                    "level_file": level_path.name,
                    "level_name": level_name,
                    "algorithm": algorithm,
                    "run": run_number,
                    "found": result["found"],
                    "time_sec": result["time_sec"],
                    "peak_memory_bytes": result[
                        "peak_memory_bytes"
                    ],
                    "expanded_nodes": result[
                        "expanded_nodes"
                    ],
                    "solution_length": result[
                        "solution_length"
                    ],
                    "total_cost": (
                        ""
                        if result["total_cost"]
                        is None
                        else result[
                            "total_cost"
                        ]
                    ),
                }

                rows.append(row)

                print(
                    f"[{case_index}/{total_cases}] "
                    f"{level_path.name} | "
                    f"{algorithm} | "
                    f"run {run_number} | "
                    f"found={result['found']}"
                )

    results_path = (
        RESULTS_DIR
        / "results.csv"
    )

    write_results_csv(
        results_path,
        rows,
    )

    summary_rows = build_summary(
        rows
    )

    summary_path = (
        RESULTS_DIR
        / "summary.csv"
    )

    write_summary_csv(
        summary_path,
        summary_rows,
    )

    print()
    print(
        f"Saved raw results to: "
        f"{results_path}"
    )
    print(
        f"Saved summary to: "
        f"{summary_path}"
    )


def write_results_csv(
    file_path,
    rows,
):
    fieldnames = [
        "level_file",
        "level_name",
        "algorithm",
        "run",
        "found",
        "time_sec",
        "peak_memory_bytes",
        "expanded_nodes",
        "solution_length",
        "total_cost",
    ]

    with file_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


def build_summary(rows):
    groups = {}

    for row in rows:
        key = (
            row["level_file"],
            row["level_name"],
            row["algorithm"],
        )

        groups.setdefault(
            key,
            [],
        ).append(
            row
        )

    summary_rows = []

    for (
        level_file,
        level_name,
        algorithm,
    ), group_rows in groups.items():

        found_count = sum(
            1
            for row in group_rows
            if row["found"]
        )

        times = [
            float(row["time_sec"])
            for row in group_rows
        ]

        memories = [
            float(
                row[
                    "peak_memory_bytes"
                ]
            )
            for row in group_rows
        ]

        expanded = [
            float(
                row[
                    "expanded_nodes"
                ]
            )
            for row in group_rows
        ]

        lengths = [
            float(
                row[
                    "solution_length"
                ]
            )
            for row in group_rows
        ]

        costs = [
            float(row["total_cost"])
            for row in group_rows
            if row["total_cost"] != ""
        ]

        summary_rows.append(
            {
                "level_file": level_file,
                "level_name": level_name,
                "algorithm": algorithm,
                "runs": len(
                    group_rows
                ),
                "found_runs": found_count,
                "mean_time_sec": statistics.mean(
                    times
                ),
                "median_time_sec": statistics.median(
                    times
                ),
                "mean_peak_memory_bytes": statistics.mean(
                    memories
                ),
                "median_peak_memory_bytes": statistics.median(
                    memories
                ),
                "mean_expanded_nodes": statistics.mean(
                    expanded
                ),
                "mean_solution_length": statistics.mean(
                    lengths
                ),
                "mean_total_cost": (
                    statistics.mean(
                        costs
                    )
                    if costs
                    else ""
                ),
            }
        )

    summary_rows.sort(
        key=lambda row: (
            row["level_file"],
            ALGORITHMS.index(
                row["algorithm"]
            ),
        )
    )

    return summary_rows


def write_summary_csv(
    file_path,
    rows,
):
    fieldnames = [
        "level_file",
        "level_name",
        "algorithm",
        "runs",
        "found_runs",
        "mean_time_sec",
        "median_time_sec",
        "mean_peak_memory_bytes",
        "median_peak_memory_bytes",
        "mean_expanded_nodes",
        "mean_solution_length",
        "mean_total_cost",
    ]

    with file_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


if __name__ == "__main__":
    run_benchmark()