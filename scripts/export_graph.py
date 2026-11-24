"""Loads a road graph from .graphml into csv.

data/nodes.csv - idx, osm_id, lat, lon
data/edges.csv - u, v, length_cm  (u, v - indices 0..n-1)
data/cases.csv - src, dst, dist_cm, python_ms (reference for testing)
"""

import argparse
import csv
import random
import time
from pathlib import Path

import networkx as nx
import osmnx as ox

DEFAULT_GRAPH = r"D:\Graphmap\graphmap-algorithms\ukraine_graph.graphml"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", default=DEFAULT_GRAPH)
    parser.add_argument("--out", default="data")
    parser.add_argument("--cases", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True)

    print(f"Loading {args.graph}...")
    G = ox.load_graphml(args.graph)

    largest = max(nx.strongly_connected_components(G), key=len)
    G = G.subgraph(largest).copy()

    osm_ids = list(G.nodes)
    index = {osm_id: i for i, osm_id in enumerate(osm_ids)}

    with open(out / "nodes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "osm_id", "lat", "lon"])
        for i, osm_id in enumerate(osm_ids):
            node = G.nodes[osm_id]
            w.writerow([i, osm_id, node["y"], node["x"]])

    best: dict[tuple[int, int], int] = {}
    for u, v, data in G.edges(data=True):
        if u == v:
            continue  # loop edges are not useful for routing

        key = (index[u], index[v])
        length_cm = round(data["length"] * 100)
        if key not in best or length_cm < best[key]:
            best[key] = length_cm

    with open(out / "edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["u", "v", "length_cm"])
        for (u, v), length_cm in sorted(best.items()):
            w.writerow([u, v, length_cm])

    # Reference count on the same graph with the same weights
    # that is going to rust - then lengths must be the same
    D = nx.DiGraph()
    D.add_nodes_from(range(len(osm_ids)))
    D.add_weighted_edges_from((u, v, w) for (u, v), w in best.items())

    rng = random.Random(args.seed)
    n = D.number_of_nodes()
    with open(out / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["src", "dst", "dist_cm", "python_ms"])
        for _ in range(args.cases):
            s, t = rng.randrange(n), rng.randrange(n)
            start = time.perf_counter()
            dist = nx.dijkstra_path_length(D, s, t, weight="weight")
            ms = (time.perf_counter() - start) * 1000
            w.writerow([s, t, dist, f"{ms:.2f}"])

    print(f"nodes: {n}, edges: {len(best)}, cases: {args.cases} -> {out.resolve()}")


if __name__ == "__main__":
    main()
