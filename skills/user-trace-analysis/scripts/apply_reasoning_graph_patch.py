#!/usr/bin/env python3
"""Apply a follow-up evidence patch to a ManiScope reasoning graph."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from reasoning_graph_to_forest import (
    GraphError,
    build_forest,
    read_json,
    validate_graph,
    write_outputs,
)


ALLOWED_OPS = {"add_node", "add_edge", "update_node", "add_root"}
ALLOWED_ACTORS = {"agent", "user", "system"}
REQUIRED_PATCH_NODE_FIELDS = {
    "actor",
    "source",
    "planRef",
    "explanation",
    "evidenceSummary",
    "reasoningRole",
    "patchRationale",
}


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GraphError(f"{path} must be a non-empty string")
    return value


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GraphError(f"{path} must be an object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise GraphError(f"{path} must be a list")
    return value


def validate_patch_node(node: dict[str, Any], index: int) -> None:
    node_id = require_string(node.get("id"), f"operations[{index}].node.id")
    missing = sorted(field for field in REQUIRED_PATCH_NODE_FIELDS if field not in node)
    if missing:
        raise GraphError(
            f"add_node operation for {node_id} is missing follow-up fields: {', '.join(missing)}"
        )

    actor = require_string(node.get("actor"), f"add_node {node_id}.actor")
    if actor not in ALLOWED_ACTORS:
        raise GraphError(f"add_node {node_id}.actor must be one of {sorted(ALLOWED_ACTORS)}")

    require_string(node.get("source"), f"add_node {node_id}.source")
    require_string(node.get("explanation"), f"add_node {node_id}.explanation")
    require_string(node.get("evidenceSummary"), f"add_node {node_id}.evidenceSummary")
    require_string(node.get("reasoningRole"), f"add_node {node_id}.reasoningRole")
    require_string(node.get("patchRationale"), f"add_node {node_id}.patchRationale")
    plan_ref = require_object(node.get("planRef"), f"add_node {node_id}.planRef")
    if not plan_ref:
        raise GraphError(f"add_node {node_id}.planRef must not be empty")


def validate_patch(patch: dict[str, Any]) -> list[dict[str, Any]]:
    if patch.get("version") != 1:
        raise GraphError("patch.version must be 1")
    require_string(patch.get("runId"), "patch.runId")
    operations = require_list(patch.get("operations"), "patch.operations")
    if not operations:
        raise GraphError("patch.operations must not be empty")

    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise GraphError(f"operations[{index}] must be an object")
        op = require_string(operation.get("op"), f"operations[{index}].op")
        if op not in ALLOWED_OPS:
            raise GraphError(f"operations[{index}] has unknown op: {op}")
        if op == "add_node":
            validate_patch_node(require_object(operation.get("node"), f"operations[{index}].node"), index)
        elif op == "add_edge":
            require_object(operation.get("edge"), f"operations[{index}].edge")
        elif op == "update_node":
            require_string(operation.get("id"), f"operations[{index}].id")
            updates = require_object(operation.get("set"), f"operations[{index}].set")
            if not updates:
                raise GraphError(f"operations[{index}].set must not be empty")
            if "id" in updates:
                raise GraphError(f"operations[{index}].set must not change node id")
        elif op == "add_root":
            require_string(operation.get("id"), f"operations[{index}].id")

    return operations


def edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return str(edge.get("source")), str(edge.get("target")), str(edge.get("relation"))


def apply_patch(base_graph: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    _base_nodes, _base_edges, base_roots = validate_graph(base_graph)
    operations = validate_patch(patch)

    graph = copy.deepcopy(base_graph)
    graph.setdefault("nodes", [])
    graph.setdefault("edges", [])
    if "roots" not in graph:
        graph["roots"] = base_roots

    nodes_by_id = {node["id"]: node for node in graph["nodes"]}
    edge_keys = {edge_key(edge) for edge in graph["edges"]}

    for index, operation in enumerate(operations):
        op = operation["op"]
        if op == "add_node":
            node = copy.deepcopy(operation["node"])
            node_id = node["id"]
            if node_id in nodes_by_id:
                raise GraphError(f"operations[{index}] add_node duplicates existing node: {node_id}")
            graph["nodes"].append(node)
            nodes_by_id[node_id] = node
            continue

        if op == "add_edge":
            edge = copy.deepcopy(operation["edge"])
            key = edge_key(edge)
            if key in edge_keys:
                raise GraphError(
                    f"operations[{index}] add_edge duplicates existing edge: {key[0]} -> {key[1]} ({key[2]})"
                )
            graph["edges"].append(edge)
            edge_keys.add(key)
            continue

        if op == "update_node":
            node_id = operation["id"]
            if node_id not in nodes_by_id:
                raise GraphError(f"operations[{index}] update_node references missing node: {node_id}")
            nodes_by_id[node_id].update(copy.deepcopy(operation["set"]))
            continue

        if op == "add_root":
            root_id = operation["id"]
            if root_id in graph["roots"]:
                raise GraphError(f"operations[{index}] add_root duplicates existing root: {root_id}")
            graph["roots"].append(root_id)
            continue

        raise GraphError(f"operations[{index}] has unsupported op: {op}")

    graph.setdefault("patchesApplied", [])
    graph["patchesApplied"].append(
        {
            "runId": patch["runId"],
            "description": patch.get("description", ""),
            "operationCount": len(operations),
        }
    )

    validate_graph(graph)
    return graph


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply reasoning-graph-patch JSON and regenerate augmented forests."
    )
    parser.add_argument("graph", type=Path, help="Path to reasoning-graph.json")
    parser.add_argument("patch", type=Path, help="Path to reasoning-graph-patch-*.json")
    parser.add_argument("--out", type=Path, help="Output path for augmented-reasoning-graph.json")
    parser.add_argument("--forest-json-out", type=Path, help="Output path for augmented forest JSON")
    parser.add_argument("--forest-md-out", type=Path, help="Output path for augmented forest Markdown")
    parser.add_argument("--no-forest", action="store_true", help="Only write the augmented graph")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.out or args.graph.with_name("augmented-reasoning-graph.json")
    forest_json_out = args.forest_json_out or out.with_name("augmented-reasoning-forest.json")
    forest_md_out = args.forest_md_out or out.with_name("augmented-reasoning-forest.md")

    try:
        base_graph = read_json(args.graph)
        patch = read_json(args.patch)
        augmented_graph = apply_patch(base_graph, patch)
        write_json(out, augmented_graph)
        print(f"wrote {out}")

        if not args.no_forest:
            nodes, edges, roots = validate_graph(augmented_graph)
            forest = build_forest(augmented_graph, nodes, edges, roots)
            write_outputs(forest, forest_json_out, forest_md_out)
            print(f"wrote {forest_json_out}")
            print(f"wrote {forest_md_out}")
    except GraphError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
