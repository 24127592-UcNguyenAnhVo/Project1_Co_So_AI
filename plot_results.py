import csv
from pathlib import Path
from xml.sax.saxutils import escape


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
CHARTS_DIR = RESULTS_DIR / "charts"
SUMMARY_FILE = RESULTS_DIR / "summary.csv"

ALGORITHMS = [
    "BFS",
    "DFS",
    "UCS",
    "A*",
]


def read_summary():
    if not SUMMARY_FILE.exists():
        raise FileNotFoundError(
            "results/summary.csv does not exist. "
            "Run benchmark.py first."
        )

    with SUMMARY_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def build_lookup(rows):
    level_order = []
    lookup = {}

    for row in rows:
        level_file = row["level_file"]

        if level_file not in level_order:
            level_order.append(level_file)

        lookup[
            (
                level_file,
                row["algorithm"],
            )
        ] = row

    return level_order, lookup


def parse_metric_value(
    row,
    metric,
    scale,
):
    if row is None:
        return 0.0

    raw_value = row.get(
        metric,
        "",
    )

    if raw_value in (
        "",
        None,
    ):
        return 0.0

    return float(raw_value) / scale


def create_grouped_bar_chart(
    rows,
    metric,
    title,
    ylabel,
    output_name,
    scale=1.0,
):
    level_order, lookup = build_lookup(
        rows
    )

    if not level_order:
        raise ValueError(
            "No benchmark rows were found."
        )

    values_by_algorithm = {}

    all_values = []

    for algorithm in ALGORITHMS:
        algorithm_values = []

        for level_file in level_order:
            row = lookup.get(
                (
                    level_file,
                    algorithm,
                )
            )

            value = parse_metric_value(
                row,
                metric,
                scale,
            )

            algorithm_values.append(
                value
            )

            all_values.append(
                value
            )

        values_by_algorithm[
            algorithm
        ] = algorithm_values

    max_value = max(
        all_values,
        default=0.0,
    )

    if max_value <= 0:
        max_value = 1.0

    width = 1200
    height = 700

    margin_left = 110
    margin_right = 40
    margin_top = 80
    margin_bottom = 150

    plot_width = (
        width
        - margin_left
        - margin_right
    )

    plot_height = (
        height
        - margin_top
        - margin_bottom
    )

    group_width = (
        plot_width
        / len(level_order)
    )

    usable_group_width = (
        group_width
        * 0.78
    )

    bar_width = (
        usable_group_width
        / len(ALGORITHMS)
    )

    colors = [
        "#4C78A8",
        "#F58518",
        "#54A24B",
        "#E45756",
    ]

    svg = []

    svg.append(
        '<?xml version="1.0" encoding="UTF-8"?>'
    )

    svg.append(
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        )
    )

    svg.append(
        '<rect width="100%" height="100%" fill="white"/>'
    )

    svg.append(
        (
            f'<text x="{width / 2}" y="35" '
            f'text-anchor="middle" '
            f'font-family="Arial" '
            f'font-size="24" '
            f'font-weight="bold">'
            f'{escape(title)}'
            f'</text>'
        )
    )

    # Y-axis grid and labels
    tick_count = 5

    for tick in range(
        tick_count + 1
    ):
        ratio = (
            tick
            / tick_count
        )

        value = (
            max_value
            * ratio
        )

        y = (
            margin_top
            + plot_height
            - ratio
            * plot_height
        )

        svg.append(
            (
                f'<line x1="{margin_left}" '
                f'y1="{y:.2f}" '
                f'x2="{width - margin_right}" '
                f'y2="{y:.2f}" '
                f'stroke="#dddddd" '
                f'stroke-width="1"/>'
            )
        )

        svg.append(
            (
                f'<text x="{margin_left - 10}" '
                f'y="{y + 5:.2f}" '
                f'text-anchor="end" '
                f'font-family="Arial" '
                f'font-size="12">'
                f'{value:.4g}'
                f'</text>'
            )
        )

    # Axes
    svg.append(
        (
            f'<line x1="{margin_left}" '
            f'y1="{margin_top}" '
            f'x2="{margin_left}" '
            f'y2="{margin_top + plot_height}" '
            f'stroke="black" '
            f'stroke-width="2"/>'
        )
    )

    svg.append(
        (
            f'<line x1="{margin_left}" '
            f'y1="{margin_top + plot_height}" '
            f'x2="{width - margin_right}" '
            f'y2="{margin_top + plot_height}" '
            f'stroke="black" '
            f'stroke-width="2"/>'
        )
    )

    # Bars
    for level_index, level_file in enumerate(
        level_order
    ):
        group_start = (
            margin_left
            + level_index
            * group_width
            + (
                group_width
                - usable_group_width
            ) / 2
        )

        for algorithm_index, algorithm in enumerate(
            ALGORITHMS
        ):
            value = (
                values_by_algorithm[
                    algorithm
                ][
                    level_index
                ]
            )

            bar_height = (
                value
                / max_value
                * plot_height
            )

            x = (
                group_start
                + algorithm_index
                * bar_width
            )

            y = (
                margin_top
                + plot_height
                - bar_height
            )

            svg.append(
                (
                    f'<rect x="{x:.2f}" '
                    f'y="{y:.2f}" '
                    f'width="{max(bar_width - 2, 1):.2f}" '
                    f'height="{bar_height:.2f}" '
                    f'fill="{colors[algorithm_index]}"/>'
                )
            )

        label_x = (
            margin_left
            + level_index
            * group_width
            + group_width / 2
        )

        label_y = (
            margin_top
            + plot_height
            + 24
        )

        svg.append(
            (
                f'<text x="{label_x:.2f}" '
                f'y="{label_y:.2f}" '
                f'text-anchor="end" '
                f'transform="rotate(-35 '
                f'{label_x:.2f} '
                f'{label_y:.2f})" '
                f'font-family="Arial" '
                f'font-size="12">'
                f'{escape(level_file)}'
                f'</text>'
            )
        )

    # Y axis label
    y_label_x = 28
    y_label_y = (
        margin_top
        + plot_height / 2
    )

    svg.append(
        (
            f'<text x="{y_label_x}" '
            f'y="{y_label_y:.2f}" '
            f'text-anchor="middle" '
            f'transform="rotate(-90 '
            f'{y_label_x} '
            f'{y_label_y:.2f})" '
            f'font-family="Arial" '
            f'font-size="15">'
            f'{escape(ylabel)}'
            f'</text>'
        )
    )

    # Legend
    legend_y = (
        height - 35
    )

    legend_total_width = (
        len(ALGORITHMS)
        * 120
    )

    legend_x = (
        width
        - legend_total_width
    ) / 2

    for index, algorithm in enumerate(
        ALGORITHMS
    ):
        x = (
            legend_x
            + index
            * 120
        )

        svg.append(
            (
                f'<rect x="{x:.2f}" '
                f'y="{legend_y - 14}" '
                f'width="18" '
                f'height="18" '
                f'fill="{colors[index]}"/>'
            )
        )

        svg.append(
            (
                f'<text x="{x + 26:.2f}" '
                f'y="{legend_y}" '
                f'font-family="Arial" '
                f'font-size="14">'
                f'{escape(algorithm)}'
                f'</text>'
            )
        )

    svg.append(
        '</svg>'
    )

    CHARTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        CHARTS_DIR
        / output_name
    )

    output_path.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )

    print(
        f"Saved: {output_path}"
    )


def create_all_charts():
    rows = read_summary()

    create_grouped_bar_chart(
        rows,
        metric="median_time_sec",
        title="Search Time Comparison",
        ylabel="Median Search Time (seconds)",
        output_name="search_time.svg",
    )

    create_grouped_bar_chart(
        rows,
        metric="median_peak_memory_bytes",
        title="Peak Memory Comparison",
        ylabel="Median Peak Memory (KB)",
        output_name="peak_memory.svg",
        scale=1024.0,
    )

    create_grouped_bar_chart(
        rows,
        metric="mean_expanded_nodes",
        title="Expanded Nodes Comparison",
        ylabel="Mean Expanded Nodes",
        output_name="expanded_nodes.svg",
    )

    create_grouped_bar_chart(
        rows,
        metric="mean_solution_length",
        title="Solution Length Comparison",
        ylabel="Mean Solution Length",
        output_name="solution_length.svg",
    )

    create_grouped_bar_chart(
        rows,
        metric="mean_total_cost",
        title="Total Cost Comparison",
        ylabel="Mean Total Cost",
        output_name="total_cost.svg",
    )


if __name__ == "__main__":
    create_all_charts()