#!/usr/bin/env python3
"""Convert a ManiScope reasoning support graph into hypothesis-rooted trees."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ALLOWED_RELATIONS = {
    "motivates",
    "produces",
    "answers",
    "supports",
    "refines",
    "contradicts",
    "contains",
    "derived_from",
}

ALLOWED_KINDS = {
    "Interaction",
    "Task",
    "AnalyticQuestion",
    "Hypothesis",
    "AnalyticActivity",
    "InvestigationStrategy",
    "Finding",
}

ALLOWED_SPACES = {"Intention", "Action", "Finding"}

ALLOWED_SCOPES = {"Low", "Mid", "High"}

ALLOWED_INTERACTION_TYPES = {
    "Data Action",
    "Model Action",
    "Visualization Action",
    "Synthesis Action",
}

ALLOWED_ACTIVITY_TYPES = {
    "Visual Analysis",
    "Statistical Analysis",
}

ALLOWED_SALIENCE = {"primary", "supporting", "low"}

KIND_ALLOWED_SPACES = {
    "Interaction": {"Action"},
    "Task": {"Intention"},
    "AnalyticQuestion": {"Intention"},
    "Hypothesis": {"Intention"},
    "AnalyticActivity": {"Action"},
    "InvestigationStrategy": {"Action"},
    "Finding": {"Finding"},
}

KIND_ALLOWED_SCOPES = {
    "Interaction": {"Low"},
    "Task": {"Low"},
    "AnalyticQuestion": {"Mid"},
    "Hypothesis": {"High"},
    "AnalyticActivity": {"Mid"},
    "InvestigationStrategy": {"High"},
    "Finding": {"Low", "Mid", "High"},
}

SCOPE_RANK = {
    "Low": 1,
    "Mid": 2,
    "High": 3,
}

SALIENCE_ORDER = {
    "primary": 0,
    "supporting": 1,
    "low": 2,
}

KIND_ORDER = {
    "Hypothesis": 0,
    "Finding": 1,
    "AnalyticQuestion": 2,
    "Task": 3,
    "InvestigationStrategy": 4,
    "AnalyticActivity": 5,
    "Interaction": 6,
}

REQUIRED_EXPLANATION_KINDS = {
    "Hypothesis",
    "Finding",
    "AnalyticQuestion",
    "Task",
    "InvestigationStrategy",
    "AnalyticActivity",
}

DETAIL_FIELDS = (
    "explanation",
    "evidenceSummary",
    "reasoningRole",
    "patchRationale",
)

FOREST_NODE_OPTIONAL_FIELDS = (
    "actor",
    "source",
    "planRef",
    *DETAIL_FIELDS,
)


class GraphError(Exception):
    """Raised when a reasoning graph cannot be transformed safely."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise GraphError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GraphError(f"{path}: graph root must be an object")
    return data


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GraphError(f"{path} must be a non-empty string")
    return value


def require_string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        raise GraphError(f"{path} must be a list of non-empty strings")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise GraphError(f"{path}[{index}] must be a non-empty string")
    return value


def validate_optional_detail_fields(node: dict[str, Any], node_id: str) -> None:
    for field in DETAIL_FIELDS:
        if field in node and node[field] is not None:
            require_string(node.get(field), f"node {node_id}.{field}")


def validate_node(node: dict[str, Any], index: int, nodes: dict[str, dict[str, Any]]) -> None:
    node_id = require_string(node.get("id"), f"nodes[{index}].id")
    if node_id in nodes:
        raise GraphError(f"duplicate node id: {node_id}")

    kind = require_string(node.get("kind"), f"nodes[{index}].kind")
    if kind not in ALLOWED_KINDS:
        raise GraphError(f"node {node_id} has unknown kind: {kind}")

    space = require_string(node.get("space"), f"node {node_id}.space")
    if space not in ALLOWED_SPACES:
        raise GraphError(f"node {node_id} has unknown space: {space}")
    if space not in KIND_ALLOWED_SPACES[kind]:
        expected = ", ".join(sorted(KIND_ALLOWED_SPACES[kind]))
        raise GraphError(f"node {node_id} kind {kind} must use space: {expected}")

    scope = require_string(node.get("scope"), f"node {node_id}.scope")
    if scope not in ALLOWED_SCOPES:
        raise GraphError(f"node {node_id} has unknown scope: {scope}")
    if scope not in KIND_ALLOWED_SCOPES[kind]:
        expected = ", ".join(sorted(KIND_ALLOWED_SCOPES[kind]))
        raise GraphError(f"node {node_id} kind {kind} must use scope: {expected}")

    require_string(node.get("label"), f"node {node_id}.label")
    require_string(node.get("confidence"), f"node {node_id}.confidence")
    require_string_list(node.get("provenance"), f"node {node_id}.provenance")

    if kind == "Interaction":
        interaction_type = require_string(node.get("interactionType"), f"node {node_id}.interactionType")
        if interaction_type not in ALLOWED_INTERACTION_TYPES:
            raise GraphError(
                f"Interaction node {node_id} has unknown interactionType: {interaction_type}"
            )
        salience = require_string(node.get("salience"), f"node {node_id}.salience")
        if salience not in ALLOWED_SALIENCE:
            raise GraphError(
                f"Interaction node {node_id} has unknown salience: {salience}"
            )

    if kind == "AnalyticActivity":
        activity_type = require_string(node.get("activityType"), f"node {node_id}.activityType")
        if activity_type not in ALLOWED_ACTIVITY_TYPES:
            raise GraphError(
                f"AnalyticActivity node {node_id} has unknown activityType: {activity_type}"
            )

    requires_explanation = kind in REQUIRED_EXPLANATION_KINDS or (
        kind == "Interaction"
        and (node.get("salience") == "primary" or node.get("actor") == "agent")
    )
    if requires_explanation:
        require_string(node.get("explanation"), f"node {node_id}.explanation")
    validate_optional_detail_fields(node, node_id)


def validate_relation_direction(
    edge: dict[str, Any],
    index: int,
    nodes: dict[str, dict[str, Any]],
) -> None:
    source_id = edge["source"]
    target_id = edge["target"]
    relation = edge["relation"]
    source = nodes[source_id]
    target = nodes[target_id]
    source_space = source["space"]
    target_space = target["space"]
    source_scope = source["scope"]
    target_scope = target["scope"]

    if relation == "motivates":
        if source_space != "Intention" or target_space != "Action":
            raise GraphError(
                f"edges[{index}] motivates must point from Intention to Action"
            )
        return

    if relation == "produces":
        if source_space != "Action" or target_space != "Finding":
            raise GraphError(
                f"edges[{index}] produces must point from Action to Finding"
            )
        return

    if relation == "supports":
        if source_space != "Finding" or target_space not in {"Finding", "Intention"}:
            raise GraphError(
                f"edges[{index}] supports must point from Finding to Finding or Intention"
            )
        return

    if relation == "answers":
        if source_space != "Finding" or target.get("kind") != "AnalyticQuestion":
            raise GraphError(
                f"edges[{index}] answers must point from Finding to AnalyticQuestion"
            )
        if source_scope != "Mid":
            raise GraphError(
                f"edges[{index}] answers must use a Mid-scope Finding as source"
            )
        return

    if relation in {"refines", "contradicts"}:
        if source_space != "Finding" or target_space != "Intention":
            raise GraphError(
                f"edges[{index}] {relation} must point from Finding to Intention"
            )
        return

    if relation == "contains":
        if SCOPE_RANK[source_scope] <= SCOPE_RANK[target_scope]:
            raise GraphError(
                f"edges[{index}] contains must point from a higher-scope node to a lower-scope node"
            )
        return

    if relation == "derived_from":
        return

    raise GraphError(f"edges[{index}] has unknown relation: {relation}")


def validate_analytic_questions_answered(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
) -> str | None:
    answered_question_ids = {
        edge["target"]
        for edge in edges
        if edge.get("relation") == "answers"
    }
    unanswered_questions = [
        node_id
        for node_id, node in nodes.items()
        if node.get("kind") == "AnalyticQuestion" and node_id not in answered_question_ids
    ]
    if not unanswered_questions:
        return None
    return (
        "AnalyticQuestion nodes without incoming answers edges from Mid Findings: "
        + ", ".join(sorted(unanswered_questions))
        + ". This is allowed if the user trace does not answer them; if they are central "
        + "and answerable, investigate them and add follow-up Findings in reasoning-graph-patch*.json."
    )


def validate_graph(
    graph: dict[str, Any],
    *,
    require_answered_questions: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str]]:
    if graph.get("version") != 1:
        raise GraphError("graph.version must be 1")
    require_string(graph.get("trace"), "graph.trace")

    raw_nodes = graph.get("nodes")
    raw_edges = graph.get("edges")
    if not isinstance(raw_nodes, list):
        raise GraphError("graph.nodes must be a list")
    if not isinstance(raw_edges, list):
        raise GraphError("graph.edges must be a list")

    nodes: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            raise GraphError(f"nodes[{index}] must be an object")
        validate_node(node, index, nodes)
        nodes[node["id"]] = node

    edges: list[dict[str, Any]] = []
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            raise GraphError(f"edges[{index}] must be an object")
        source = require_string(edge.get("source"), f"edges[{index}].source")
        target = require_string(edge.get("target"), f"edges[{index}].target")
        relation = require_string(edge.get("relation"), f"edges[{index}].relation")
        if source == target:
            raise GraphError(f"edges[{index}] cannot be a self-edge: {source}")
        if source not in nodes:
            raise GraphError(f"edges[{index}] references missing source node: {source}")
        if target not in nodes:
            raise GraphError(f"edges[{index}] references missing target node: {target}")
        if relation not in ALLOWED_RELATIONS:
            raise GraphError(f"edges[{index}] has unknown relation: {relation}")
        require_string(edge.get("rationale"), f"edges[{index}].rationale")
        validate_relation_direction(edge, index, nodes)
        edges.append(edge)

    roots = graph.get("roots")
    if roots is None:
        roots = [node_id for node_id, node in nodes.items() if node.get("kind") == "Hypothesis"]
    if not isinstance(roots, list) or not all(isinstance(root, str) for root in roots):
        raise GraphError("graph.roots must be a list of node ids")
    missing_roots = [root for root in roots if root not in nodes]
    if missing_roots:
        raise GraphError(f"graph.roots references missing nodes: {', '.join(missing_roots)}")
    duplicate_roots = sorted({root for root in roots if roots.count(root) > 1})
    if duplicate_roots:
        raise GraphError(f"graph.roots contains duplicate nodes: {', '.join(duplicate_roots)}")
    non_hypothesis_roots = [root for root in roots if nodes[root].get("kind") != "Hypothesis"]
    if non_hypothesis_roots:
        raise GraphError(
            f"graph.roots must contain only Hypothesis nodes: {', '.join(non_hypothesis_roots)}"
        )
    if not roots:
        raise GraphError("no Hypothesis roots found")

    if require_answered_questions:
        warning = validate_analytic_questions_answered(nodes, edges)
        if warning:
            raise GraphError(warning)

    return nodes, edges, roots


def projected_child_parent(edge: dict[str, Any]) -> tuple[str, str, str]:
    source = edge["source"]
    target = edge["target"]
    relation = edge["relation"]
    if relation in {"produces", "answers", "supports", "refines", "contradicts"}:
        return source, target, relation
    if relation in {"motivates", "contains", "derived_from"}:
        return target, source, relation
    raise GraphError(f"unknown relation: {relation}")


def sort_child_entries(entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    def key(entry: tuple[str, str]) -> tuple[int, int, str, str]:
        child_id, relation = entry
        node = CURRENT_NODES[child_id]
        salience = SALIENCE_ORDER.get(str(node.get("salience", "supporting")), 1)
        kind = KIND_ORDER.get(str(node.get("kind", "")), 99)
        return salience, kind, child_id, relation

    return sorted(entries, key=key)


CURRENT_NODES: dict[str, dict[str, Any]] = {}


def build_forest(
    graph: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    roots: list[str],
) -> dict[str, Any]:
    global CURRENT_NODES
    CURRENT_NODES = nodes

    children_by_parent: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in edges:
        child, parent, relation = projected_child_parent(edge)
        children_by_parent[parent].append((child, relation))

    trees = []
    for root in roots:
        tree_nodes: list[dict[str, Any]] = []
        tree_edges: list[dict[str, str]] = []

        def visit(
            canonical_id: str,
            parent_instance_id: str | None,
            relation_to_parent: str | None,
            path: tuple[str, ...],
            index_path: tuple[int, ...],
        ) -> str:
            if canonical_id in path:
                cycle = " -> ".join((*path, canonical_id))
                raise GraphError(f"support projection contains a cycle: {cycle}")

            if parent_instance_id is None:
                instance_id = canonical_id
            else:
                suffix = ".".join(str(part) for part in index_path)
                instance_id = f"{canonical_id}@{root}.{suffix}"

            node = nodes[canonical_id]
            tree_node = {
                "instanceId": instance_id,
                "canonicalId": canonical_id,
                "parentInstanceId": parent_instance_id,
                "relationToParent": relation_to_parent,
                "kind": node.get("kind"),
                "space": node.get("space"),
                "scope": node.get("scope"),
                "label": node.get("label", canonical_id),
                "confidence": node.get("confidence"),
                "salience": node.get("salience"),
                "interactionType": node.get("interactionType"),
                "activityType": node.get("activityType"),
                "provenance": node.get("provenance", []),
            }
            for field in FOREST_NODE_OPTIONAL_FIELDS:
                if field in node and node[field] is not None:
                    tree_node[field] = node[field]
            tree_nodes.append(tree_node)
            if parent_instance_id is not None and relation_to_parent is not None:
                tree_edges.append(
                    {
                        "source": instance_id,
                        "target": parent_instance_id,
                        "relation": relation_to_parent,
                    }
                )

            child_entries = sort_child_entries(children_by_parent.get(canonical_id, []))
            for child_index, (child_id, relation) in enumerate(child_entries, start=1):
                visit(child_id, instance_id, relation, (*path, canonical_id), (*index_path, child_index))

            return instance_id

        visit(root, None, None, tuple(), tuple())
        validate_tree_leaves(root, tree_nodes, tree_edges)
        trees.append(
            {
                "root": root,
                "rootLabel": nodes[root].get("label", root),
                "nodes": tree_nodes,
                "edges": tree_edges,
            }
        )

    return {
        "version": 1,
        "sourceTrace": graph.get("trace"),
        "sourceGraphVersion": graph.get("version"),
        "trees": trees,
    }


def validate_tree_leaves(
    root: str,
    tree_nodes: list[dict[str, Any]],
    tree_edges: list[dict[str, str]],
) -> None:
    if not tree_edges:
        raise GraphError(f"tree rooted at {root} has no support edges")

    parent_ids = {edge["target"] for edge in tree_edges}
    leaves = [node for node in tree_nodes if node["instanceId"] not in parent_ids]
    non_interaction_leaves = [
        node for node in leaves if node.get("kind") != "Interaction"
    ]
    if non_interaction_leaves:
        labels = ", ".join(
            f"{node['instanceId']} ({node.get('kind')})" for node in non_interaction_leaves
        )
        raise GraphError(
            f"tree rooted at {root} has non-Interaction leaves: {labels}"
        )


def mermaid_id(instance_id: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", instance_id)


def mermaid_label(node: dict[str, Any]) -> str:
    parts = [str(node.get("kind") or "Node")]
    salience = node.get("salience")
    if salience:
        parts.append(f"salience: {salience}")
    interaction_type = node.get("interactionType")
    if interaction_type:
        parts.append(str(interaction_type))
    activity_type = node.get("activityType")
    if activity_type:
        parts.append(str(activity_type))
    label = str(node.get("label") or node["canonicalId"])
    confidence = node.get("confidence")
    text = "\\n".join((*parts, label, str(confidence or ""))).strip()
    return text.replace("\\", "\\\\").replace('"', '\\"')


def render_markdown(forest: dict[str, Any]) -> str:
    lines = [
        "# User Reasoning Forest",
        "",
        "This file is mechanically generated from `reasoning-graph.json`. Each tree is rooted at one Hypothesis. Shared canonical nodes are duplicated into tree node instances, and each duplicate keeps its `canonicalId`.",
        "",
    ]

    for tree_index, tree in enumerate(forest["trees"], start=1):
        root = tree["root"]
        root_label = tree.get("rootLabel") or root
        lines.extend([f"## Tree {tree_index}: {root}", "", root_label, ""])
        lines.extend(
            [
                "| Instance ID | Canonical ID | Parent | Relation | Kind | Scope | Salience | Confidence | Label | Explanation | Evidence Summary | Reasoning Role |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for node in tree["nodes"]:
            lines.append(
                "| "
                + " | ".join(
                    markdown_cell(value)
                    for value in [
                        node["instanceId"],
                        node["canonicalId"],
                        node.get("parentInstanceId") or "",
                        node.get("relationToParent") or "",
                        node.get("kind") or "",
                        node.get("scope") or "",
                        node.get("salience") or "",
                        node.get("confidence") or "",
                        node.get("label") or "",
                        node.get("explanation") or "",
                        node.get("evidenceSummary") or "",
                        node.get("reasoningRole") or "",
                    ]
                )
                + " |"
            )
        lines.extend(["", "```mermaid", "flowchart BT"])
        for node in tree["nodes"]:
            lines.append(f'  {mermaid_id(node["instanceId"])}["{mermaid_label(node)}"]')
        for edge in tree["edges"]:
            lines.append(
                f'  {mermaid_id(edge["source"])} -->|{edge["relation"]}| {mermaid_id(edge["target"])}'
            )
        lines.extend(["```", ""])

    lines.extend(
        [
            "## Reading Notes",
            "",
            "- Edges point from lower-level evidence toward higher-level reasoning support.",
            "- `contradicts` edges mark counter-evidence and should be read as weakening the parent claim.",
            "- Duplicate tree nodes with the same `canonicalId` are shared graph nodes expanded mechanically for readability.",
            "- Interaction leaves are preserved by default, with `salience` indicating how central each logged user action is to the reasoning path.",
            "",
        ]
    )
    return "\n".join(lines)


def markdown_cell(value: Any) -> str:
    text = str(value)
    return text.replace("\n", "<br>").replace("|", "\\|")


def write_outputs(forest: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_out.write_text(json.dumps(forest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(forest), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert reasoning-graph.json into user-reasoning-forest.json and .md."
    )
    parser.add_argument("graph", type=Path, help="Path to reasoning-graph.json")
    parser.add_argument("--json-out", type=Path, help="Output path for user-reasoning-forest.json")
    parser.add_argument("--md-out", type=Path, help="Output path for user-reasoning-forest.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    graph_path = args.graph
    json_out = args.json_out or graph_path.with_name("user-reasoning-forest.json")
    md_out = args.md_out or graph_path.with_name("user-reasoning-forest.md")

    try:
        graph = read_json(graph_path)
        nodes, edges, roots = validate_graph(graph)
        warning = validate_analytic_questions_answered(nodes, edges)
        if warning:
            print(f"warning: {warning}", file=sys.stderr)
        forest = build_forest(graph, nodes, edges, roots)
        write_outputs(forest, json_out, md_out)
    except GraphError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {json_out}")
    print(f"wrote {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
