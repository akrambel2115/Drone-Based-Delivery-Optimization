"""Render a 3D terrain view for a generated instance."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

TERRAIN_COLORSCALE = [
    [0.0, "#1f6f43"],
    [0.28, "#5ea35e"],
    [0.5, "#d6c46a"],
    [0.72, "#9d7a42"],
    [1.0, "#f2f0df"],
]


def _load_instance(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance_json", type=Path)
    parser.add_argument(
        "--stride",
        type=int,
        default=2,
        help="Surface sampling stride; increase for faster rendering on large grids.",
    )
    parser.add_argument(
        "--no-routes",
        action="store_true",
        help="Hide baseline feasible route lines.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Save the visualization as an image instead of only opening a window.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Write a standalone interactive Plotly HTML visualization.",
    )
    parser.add_argument(
        "--mode",
        choices=["3d", "topdown"],
        default="3d",
        help="Interactive HTML view mode.",
    )
    args = parser.parse_args()

    instance = _load_instance(args.instance_json)

    if args.html is not None:
        _write_plotly_html(instance, args.html, stride=max(1, args.stride), mode=args.mode)

    if args.save is None and args.html is not None:
        return 0

    _render_matplotlib(instance, args)
    return 0


def _render_matplotlib(instance: dict, args: argparse.Namespace) -> None:
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(13, 9))
    ax = fig.add_subplot(111, projection="3d")
    _plot_terrain(ax, instance, np, stride=max(1, args.stride))
    _plot_no_fly_zones(ax, instance, Poly3DCollection)
    _plot_entities(ax, instance)
    if not args.no_routes:
        _plot_routes(ax, instance, plt)

    metadata = instance["metadata"]
    ax.set_title(
        f"{metadata['instance_name']} | {metadata['scenario_type']} | "
        f"{len(instance['customers'])} customers"
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z / altitude")
    ax.view_init(elev=35, azim=-55)
    ax.legend(loc="upper left")
    fig.tight_layout()

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=180, bbox_inches="tight")
        print(f"saved {args.save}")
    else:
        plt.show()


def _plot_terrain(ax, instance: dict, np, stride: int) -> None:
    terrain = instance["terrain"]
    if not terrain["enabled"] or terrain["height_map"] is None:
        bounds = instance["metadata"]["grid_bounds"]
        xs = np.array([[0, bounds["x_size"] - 1], [0, bounds["x_size"] - 1]])
        ys = np.array([[0, 0], [bounds["y_size"] - 1, bounds["y_size"] - 1]])
        zs = np.zeros_like(xs)
    else:
        height_map = np.array(terrain["height_map"], dtype=float)
        height_map = height_map[::stride, ::stride]
        x_values = np.arange(0, terrain["x_size"], stride)[: height_map.shape[0]]
        y_values = np.arange(0, terrain["y_size"], stride)[: height_map.shape[1]]
        xs, ys = np.meshgrid(x_values, y_values, indexing="ij")
        zs = height_map

    ax.plot_surface(
        xs,
        ys,
        zs,
        cmap="terrain",
        linewidth=0,
        antialiased=True,
        alpha=0.82,
        shade=True,
    )


def _write_plotly_html(instance: dict, output_path: Path, stride: int, mode: str) -> None:
    import plotly.graph_objects as go

    figure = _build_plotly_topdown(instance, go, stride) if mode == "topdown" else _build_plotly_3d(instance, go, stride)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(
        str(output_path),
        include_plotlyjs="cdn",
        full_html=True,
        config={
            "displaylogo": False,
            "responsive": True,
            "toImageButtonOptions": {
                "format": "png",
                "filename": instance["metadata"]["instance_name"],
                "scale": 2,
            },
        },
    )
    print(f"saved {output_path}")


def _build_plotly_3d(instance: dict, go, stride: int):
    traces = [_plotly_terrain_surface(instance, go, stride)]
    traces.extend(_plotly_nfz_meshes(instance, go))
    traces.append(_plotly_depot_trace(instance, go, mode="3d"))
    traces.append(_plotly_customers_trace(instance, go, mode="3d"))
    traces.extend(_plotly_route_traces(instance, go, hidden_by_default=True, mode="3d"))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=_plotly_title(instance),
        template="plotly_white",
        legend={
            "orientation": "v",
            "yanchor": "top",
            "y": 0.98,
            "xanchor": "left",
            "x": 0.02,
            "bgcolor": "rgba(255,255,255,0.75)",
        },
        margin={"l": 0, "r": 0, "t": 90, "b": 0},
        scene={
            "xaxis_title": "x",
            "yaxis_title": "y",
            "zaxis_title": "z / altitude",
            "aspectmode": "data",
            "camera": {"eye": {"x": 1.35, "y": -1.55, "z": 1.05}},
        },
    )
    return fig


def _build_plotly_topdown(instance: dict, go, stride: int):
    heatmap = _plotly_topdown_heatmap(instance, go, stride)
    traces = [heatmap]
    traces.extend(_plotly_topdown_nfz_shapes_as_traces(instance, go))
    traces.append(_plotly_depot_trace(instance, go, mode="topdown"))
    traces.append(_plotly_customers_trace(instance, go, mode="topdown"))
    traces.extend(_plotly_route_traces(instance, go, hidden_by_default=True, mode="topdown"))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=_plotly_title(instance),
        template="plotly_white",
        xaxis_title="x",
        yaxis_title="y",
        yaxis_scaleanchor="x",
        margin={"l": 40, "r": 20, "t": 90, "b": 40},
        legend={
            "orientation": "v",
            "yanchor": "top",
            "y": 0.98,
            "xanchor": "left",
            "x": 0.02,
            "bgcolor": "rgba(255,255,255,0.75)",
        },
    )
    return fig


def _terrain_arrays(instance: dict, stride: int):
    import numpy as np

    terrain = instance["terrain"]
    if terrain["enabled"] and terrain["height_map"] is not None:
        z_values = np.array(terrain["height_map"], dtype=float)[::stride, ::stride]
        x_values = np.arange(0, terrain["x_size"], stride)[: z_values.shape[0]]
        y_values = np.arange(0, terrain["y_size"], stride)[: z_values.shape[1]]
    else:
        bounds = instance["metadata"]["grid_bounds"]
        x_values = np.array([0, bounds["x_size"] - 1])
        y_values = np.array([0, bounds["y_size"] - 1])
        z_values = np.zeros((2, 2))
    return x_values, y_values, z_values


def _plotly_terrain_surface(instance: dict, go, stride: int):
    x_values, y_values, z_values = _terrain_arrays(instance, stride)
    hover = [
        [
            f"x={int(x)}<br>y={int(y)}<br>terrain height={z_values[xi][yi]:.0f}"
            for yi, y in enumerate(y_values)
        ]
        for xi, x in enumerate(x_values)
    ]
    return go.Surface(
        x=x_values,
        y=y_values,
        z=z_values.T,
        customdata=list(map(list, zip(*hover))),
        colorscale=TERRAIN_COLORSCALE,
        opacity=0.92,
        name="terrain",
        showscale=True,
        colorbar={"title": "height", "len": 0.55},
        hovertemplate="%{customdata}<extra>terrain</extra>",
    )


def _plotly_topdown_heatmap(instance: dict, go, stride: int):
    x_values, y_values, z_values = _terrain_arrays(instance, stride)
    return go.Heatmap(
        x=x_values,
        y=y_values,
        z=z_values.T,
        colorscale=TERRAIN_COLORSCALE,
        name="terrain height",
        colorbar={"title": "height"},
        hovertemplate="x=%{x}<br>y=%{y}<br>terrain height=%{z}<extra>terrain</extra>",
    )


def _plotly_depot_trace(instance: dict, go, mode: str):
    depot = instance["depot"]
    hover = (
        f"Depot<br>x={depot['x']}<br>y={depot['y']}<br>z={depot['z']}"
    )
    if mode == "topdown":
        return go.Scatter(
            x=[depot["x"]],
            y=[depot["y"]],
            mode="markers",
            marker={"color": "#d7191c", "size": 16, "symbol": "triangle-up", "line": {"color": "white", "width": 1}},
            name="depot",
            text=[hover],
            hovertemplate="%{text}<extra></extra>",
        )
    return go.Scatter3d(
        x=[depot["x"]],
        y=[depot["y"]],
        z=[depot["z"] + 0.35],
        mode="markers",
        marker={"color": "#d7191c", "size": 8, "symbol": "diamond", "line": {"color": "white", "width": 1}},
        name="depot",
        text=[hover],
        hovertemplate="%{text}<extra></extra>",
    )


def _plotly_customers_trace(instance: dict, go, mode: str):
    customers = instance["customers"]
    demands = [customer["demand"] for customer in customers]
    min_demand = min(demands) if demands else 1
    max_demand = max(demands) if demands else 1
    sizes = [
        7 + 9 * ((demand - min_demand) / max(1, max_demand - min_demand))
        for demand in demands
    ]
    hover = [
        (
            f"Customer {customer['id']}<br>x={customer['x']}<br>y={customer['y']}"
            f"<br>z={customer['z']}<br>demand={customer['demand']}"
        )
        for customer in customers
    ]
    if mode == "topdown":
        return go.Scatter(
            x=[customer["x"] for customer in customers],
            y=[customer["y"] for customer in customers],
            mode="markers",
            marker={"color": "#2c7bb6", "size": sizes, "opacity": 0.9, "line": {"color": "white", "width": 0.7}},
            name="customers",
            text=hover,
            hovertemplate="%{text}<extra></extra>",
        )
    return go.Scatter3d(
        x=[customer["x"] for customer in customers],
        y=[customer["y"] for customer in customers],
        z=[customer["z"] + 0.45 for customer in customers],
        mode="markers",
        marker={"color": "#2c7bb6", "size": sizes, "opacity": 0.92, "line": {"color": "white", "width": 0.7}},
        name="customers",
        text=hover,
        hovertemplate="%{text}<extra></extra>",
    )


def _plotly_route_traces(instance: dict, go, hidden_by_default: bool, mode: str):
    nodes = _node_lookup(instance)
    traces = []
    colors = _route_colors()
    visible = "legendonly" if hidden_by_default else True
    for route in instance["baseline_feasible_routes"]:
        node_ids = [0] + route["customers"] + [0]
        xs = [nodes[node_id]["x"] for node_id in node_ids]
        ys = [nodes[node_id]["y"] for node_id in node_ids]
        zs = [nodes[node_id]["z"] + 1.1 for node_id in node_ids]
        text = (
            f"Route {route['route_id']}<br>"
            f"customers={len(route['customers'])}<br>"
            f"demand={route['total_demand']}<br>"
            f"energy={route['total_energy']}"
        )
        color = colors[(route["route_id"] - 1) % len(colors)]
        if mode == "topdown":
            traces.append(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line={"color": color, "width": 2},
                    opacity=0.75,
                    name=f"route {route['route_id']}",
                    visible=visible,
                    text=[text] * len(xs),
                    hovertemplate="%{text}<extra></extra>",
                )
            )
        else:
            traces.append(
                go.Scatter3d(
                    x=xs,
                    y=ys,
                    z=zs,
                    mode="lines",
                    line={"color": color, "width": 4},
                    opacity=0.75,
                    name=f"route {route['route_id']}",
                    visible=visible,
                    text=[text] * len(xs),
                    hovertemplate="%{text}<extra></extra>",
                )
            )
    return traces


def _plotly_nfz_meshes(instance: dict, go):
    traces = []
    for box in instance["no_fly_zones"]:
        vertices = _box_vertices(box)
        xs, ys, zs = zip(*vertices)
        triangles = [
            (0, 1, 2),
            (0, 2, 3),
            (4, 5, 6),
            (4, 6, 7),
            (0, 1, 5),
            (0, 5, 4),
            (1, 2, 6),
            (1, 6, 5),
            (2, 3, 7),
            (2, 7, 6),
            (3, 0, 4),
            (3, 4, 7),
        ]
        i, j, k = zip(*triangles)
        traces.append(
            go.Mesh3d(
                x=xs,
                y=ys,
                z=zs,
                i=i,
                j=j,
                k=k,
                color="#d7191c",
                opacity=0.23,
                name=f"NFZ {box['id']}",
                text=[_nfz_hover_text(box)] * len(xs),
                hovertemplate="%{text}<extra></extra>",
                showlegend=True,
            )
        )
    return traces


def _plotly_topdown_nfz_shapes_as_traces(instance: dict, go):
    traces = []
    for box in instance["no_fly_zones"]:
        xs = [box["x_min"], box["x_max"], box["x_max"], box["x_min"], box["x_min"]]
        ys = [box["y_min"], box["y_min"], box["y_max"], box["y_max"], box["y_min"]]
        traces.append(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                fill="toself",
                fillcolor="rgba(215,25,28,0.25)",
                line={"color": "rgba(120,0,0,0.85)", "width": 1},
                name=f"NFZ {box['id']}",
                text=[_nfz_hover_text(box)] * len(xs),
                hovertemplate="%{text}<extra></extra>",
            )
        )
    return traces


def _plotly_title(instance: dict) -> str:
    metadata = instance["metadata"]
    profile = instance["drone_profile"]
    counts = metadata["counts"]
    fleet = profile["fleet_size"] if profile["fleet_size"] is not None else "unlimited"
    return (
        f"{metadata['instance_name']} ({metadata['scenario_type']})"
        f"<br><sup>{counts['customers']} customers | {counts['no_fly_zones']} NFZs | "
        f"fleet={fleet} | battery={profile['battery_capacity']} | "
        f"payload={profile['payload_capacity']}</sup>"
    )


def _node_lookup(instance: dict) -> dict[int, dict]:
    nodes = {0: instance["depot"]}
    nodes.update({customer["id"]: customer for customer in instance["customers"]})
    return nodes


def _nfz_hover_text(box: dict) -> str:
    return (
        f"NFZ {box['id']}<br>"
        f"x=[{box['x_min']}, {box['x_max']}]<br>"
        f"y=[{box['y_min']}, {box['y_max']}]<br>"
        f"z=[{box['z_min']}, {box['z_max']}]"
    )


def _route_colors() -> list[str]:
    return [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]


def _plot_entities(ax, instance: dict) -> None:
    depot = instance["depot"]
    ax.scatter(
        [depot["x"]],
        [depot["y"]],
        [depot["z"] + 0.35],
        c="#d7191c",
        s=110,
        marker="^",
        edgecolor="white",
        linewidth=0.8,
        label="depot",
        depthshade=False,
    )
    customers = instance["customers"]
    ax.scatter(
        [c["x"] for c in customers],
        [c["y"] for c in customers],
        [c["z"] + 0.45 for c in customers],
        c="#2c7bb6",
        s=24,
        edgecolor="white",
        linewidth=0.35,
        label="customers",
        depthshade=False,
    )


def _plot_routes(ax, instance: dict, plt) -> None:
    nodes = {0: instance["depot"]}
    nodes.update({customer["id"]: customer for customer in instance["customers"]})
    colors = plt.cm.tab20.colors
    for route in instance["baseline_feasible_routes"]:
        node_ids = [0] + route["customers"] + [0]
        xs = [nodes[node_id]["x"] for node_id in node_ids]
        ys = [nodes[node_id]["y"] for node_id in node_ids]
        zs = [nodes[node_id]["z"] + 1.1 for node_id in node_ids]
        color = colors[(route["route_id"] - 1) % len(colors)]
        ax.plot(
            xs,
            ys,
            zs,
            color=color,
            linewidth=1.2,
            alpha=0.8,
            label="baseline routes" if route["route_id"] == 1 else None,
        )


def _plot_no_fly_zones(ax, instance: dict, poly_collection_cls) -> None:
    for index, box in enumerate(instance["no_fly_zones"]):
        vertices = _box_vertices(box)
        faces = [
            [vertices[i] for i in [0, 1, 2, 3]],
            [vertices[i] for i in [4, 5, 6, 7]],
            [vertices[i] for i in [0, 1, 5, 4]],
            [vertices[i] for i in [2, 3, 7, 6]],
            [vertices[i] for i in [1, 2, 6, 5]],
            [vertices[i] for i in [0, 3, 7, 4]],
        ]
        collection = poly_collection_cls(
            faces,
            facecolors=(0.08, 0.08, 0.08, 0.28),
            edgecolors=(0.02, 0.02, 0.02, 0.85),
            linewidths=0.8,
        )
        ax.add_collection3d(collection)
        if index == 0:
            center = (
                (box["x_min"] + box["x_max"]) / 2,
                (box["y_min"] + box["y_max"]) / 2,
                (box["z_min"] + box["z_max"]) / 2,
            )
            ax.scatter(
                [center[0]],
                [center[1]],
                [center[2]],
                c="black",
                marker="s",
                s=36,
                label="no-fly zones",
                depthshade=False,
            )


def _box_vertices(box: dict) -> list[tuple[float, float, float]]:
    x0, x1 = box["x_min"], box["x_max"]
    y0, y1 = box["y_min"], box["y_max"]
    z0, z1 = box["z_min"], box["z_max"]
    return [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]


if __name__ == "__main__":
    raise SystemExit(main())
