#!/usr/bin/env python3
"""Convert a ManiScope recommendation plan graph into readable plan forests."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_KINDS = {
    "SourceNode",
    "Hypothesis",
    "ReasoningGap",
    "ExpansionRationale",
    "InvestigationStrategy",
    "AnalyticActivity",
    "RecommendedInteraction",
    "ExpectedFinding",
}

ALLOWED_RECOMMENDATION_TYPES = {"Evidence Completion", "Hypothesis Expansion"}
ALLOWED_ACTIVITY_TYPES = {"Visual Analysis", "Statistical Analysis"}
ALLOWED_INTERACTION_TYPES = {
    "Data Action",
    "Model Action",
    "Visualization Action",
    "Synthesis Action",
}
ALLOWED_RELATIONS = {
    "has_gap",
    "expands_from",
    "has_rationale",
    "addressed_by",
    "tested_by",
    "contains",
    "expects",
}

KIND_ORDER = {
    "SourceNode": 0,
    "Hypothesis": 1,
    "ReasoningGap": 2,
    "ExpansionRationale": 3,
    "InvestigationStrategy": 4,
    "AnalyticActivity": 5,
    "RecommendedInteraction": 6,
    "ExpectedFinding": 7,
}


class PlanError(Exception):
    """Raised when a recommendation plan graph is invalid."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise PlanError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanError(f"{path}: plan root must be an object")
    return data


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{path} must be a non-empty string")
    return value


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise PlanError(f"{path} must be a boolean")
    return value


def validate_node(node: dict[str, Any], index: int, nodes: dict[str, dict[str, Any]]) -> None:
    node_id = require_string(node.get("id"), f"nodes[{index}].id")
    if node_id in nodes:
        raise PlanError(f"duplicate node id: {node_id}")

    kind = require_string(node.get("kind"), f"node {node_id}.kind")
    if kind not in ALLOWED_KINDS:
        raise PlanError(f"node {node_id} has unknown kind: {kind}")

    require_string(node.get("label"), f"node {node_id}.label")
    recommendation_type = require_string(
        node.get("recommendationType"), f"node {node_id}.recommendationType"
    )
    if recommendation_type not in ALLOWED_RECOMMENDATION_TYPES:
        raise PlanError(
            f"node {node_id} has unknown recommendationType: {recommendation_type}"
        )
    require_string(node.get("status"), f"node {node_id}.status")

    if kind == "SourceNode":
        require_string(node.get("canonicalId"), f"node {node_id}.canonicalId")
    elif kind == "Hypothesis":
        hypothesis_status = require_string(
            node.get("hypothesisStatus"), f"node {node_id}.hypothesisStatus"
        )
        if hypothesis_status not in {"existing", "proposed"}:
            raise PlanError(
                f"node {node_id}.hypothesisStatus must be existing or proposed"
            )
    elif kind == "ReasoningGap":
        require_string(node.get("targetNodeId"), f"node {node_id}.targetNodeId")
        require_string(node.get("gapType"), f"node {node_id}.gapType")
        require_string(node.get("desiredSupport"), f"node {node_id}.desiredSupport")
    elif kind == "ExpansionRationale":
        require_string(node.get("sourceNodeId"), f"node {node_id}.sourceNodeId")
    elif kind == "AnalyticActivity":
        activity_type = require_string(node.get("activityType"), f"node {node_id}.activityType")
        if activity_type not in ALLOWED_ACTIVITY_TYPES:
            raise PlanError(f"node {node_id} has unknown activityType: {activity_type}")
    elif kind == "RecommendedInteraction":
        interaction_type = require_string(
            node.get("interactionType"), f"node {node_id}.interactionType"
        )
        if interaction_type not in ALLOWED_INTERACTION_TYPES:
            raise PlanError(
                f"node {node_id} has unknown interactionType: {interaction_type}"
            )
    elif kind == "ExpectedFinding":
        expected_only = require_bool(node.get("expectedOnly"), f"node {node_id}.expectedOnly")
        if expected_only is not True:
            raise PlanError(f"node {node_id}.expectedOnly must be true")


def validate_relation(edge: dict[str, Any], index: int, nodes: dict[str, dict[str, Any]]) -> None:
    source_id = require_string(edge.get("source"), f"edges[{index}].source")
    target_id = require_string(edge.get("target"), f"edges[{index}].target")
    relation = require_string(edge.get("relation"), f"edges[{index}].relation")
    if source_id == target_id:
        raise PlanError(f"edges[{index}] cannot be a self-edge: {source_id}")
    if source_id not in nodes:
        raise PlanError(f"edges[{index}] references missing source node: {source_id}")
    if target_id not in nodes:
        raise PlanError(f"edges[{index}] references missing target node: {target_id}")
    if relation not in ALLOWED_RELATIONS:
        raise PlanError(f"edges[{index}] has unknown relation: {relation}")

    source_kind = nodes[source_id]["kind"]
    target_kind = nodes[target_id]["kind"]
    if relation == "has_gap" and not (
        source_kind in {"SourceNode", "Hypothesis"} and target_kind == "ReasoningGap"
    ):
        raise PlanError(f"edges[{index}] has_gap must target a ReasoningGap")
    if relation == "expands_from" and not (
        source_kind == "SourceNode" and target_kind == "Hypothesis"
    ):
        raise PlanError(f"edges[{index}] expands_from must be SourceNode -> Hypothesis")
    if relation == "has_rationale" and not (
        source_kind == "Hypothesis" and target_kind == "ExpansionRationale"
    ):
        raise PlanError(
            f"edges[{index}] has_rationale must be Hypothesis -> ExpansionRationale"
        )
    if relation == "addressed_by" and not (
        source_kind == "ReasoningGap" and target_kind == "InvestigationStrategy"
    ):
        raise PlanError(
            f"edges[{index}] addressed_by must be ReasoningGap -> InvestigationStrategy"
        )
    if relation == "tested_by" and not (
        source_kind == "Hypothesis" and target_kind == "InvestigationStrategy"
    ):
        raise PlanError(
            f"edges[{index}] tested_by must be Hypothesis -> InvestigationStrategy"
        )
    if relation == "contains" and not (
        (source_kind == "InvestigationStrategy" and target_kind == "AnalyticActivity")
        or (source_kind == "AnalyticActivity" and target_kind == "RecommendedInteraction")
    ):
        raise PlanError(
            f"edges[{index}] contains must be Strategy -> Activity or Activity -> RecommendedInteraction"
        )
    if relation == "expects" and not (
        source_kind in {"RecommendedInteraction", "AnalyticActivity"}
        and target_kind == "ExpectedFinding"
    ):
        raise PlanError(
            f"edges[{index}] expects must be RecommendedInteraction/AnalyticActivity -> ExpectedFinding"
        )


def validate_plan(plan: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]], list[str]]:
    if plan.get("version") != 1:
        raise PlanError("plan.version must be 1")
    require_string(plan.get("trace"), "plan.trace")
    raw_nodes = plan.get("nodes")
    raw_edges = plan.get("edges")
    if not isinstance(raw_nodes, list):
        raise PlanError("plan.nodes must be a list")
    if not isinstance(raw_edges, list):
        raise PlanError("plan.edges must be a list")

    nodes: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            raise PlanError(f"nodes[{index}] must be an object")
        validate_node(node, index, nodes)
        nodes[node["id"]] = node

    edges: list[dict[str, str]] = []
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            raise PlanError(f"edges[{index}] must be an object")
        validate_relation(edge, index, nodes)
        edges.append(
            {
                "source": edge["source"],
                "target": edge["target"],
                "relation": edge["relation"],
            }
        )

    roots = plan.get("roots")
    if not isinstance(roots, list) or not all(isinstance(root, str) for root in roots):
        raise PlanError("plan.roots must be a list of node ids")
    if not roots:
        raise PlanError("plan.roots must not be empty")
    missing_roots = [root for root in roots if root not in nodes]
    if missing_roots:
        raise PlanError(f"plan.roots references missing nodes: {', '.join(missing_roots)}")
    duplicate_roots = sorted({root for root in roots if roots.count(root) > 1})
    if duplicate_roots:
        raise PlanError(f"plan.roots contains duplicate nodes: {', '.join(duplicate_roots)}")

    return nodes, edges, roots


def build_forest(
    plan: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, str]],
    roots: list[str],
) -> dict[str, Any]:
    children_by_parent: dict[str, list[tuple[str, str]]] = {}
    for edge in edges:
        children_by_parent.setdefault(edge["source"], []).append((edge["target"], edge["relation"]))

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
        ) -> None:
            if canonical_id in path:
                cycle = " -> ".join((*path, canonical_id))
                raise PlanError(f"plan projection contains a cycle: {cycle}")

            if parent_instance_id is None:
                instance_id = canonical_id
            else:
                suffix = ".".join(str(part) for part in index_path)
                instance_id = f"{canonical_id}@{root}.{suffix}"

            node = nodes[canonical_id]
            tree_nodes.append(
                {
                    "instanceId": instance_id,
                    "canonicalId": canonical_id,
                    "parentInstanceId": parent_instance_id,
                    "relationToParent": relation_to_parent,
                    "kind": node.get("kind"),
                    "label": node.get("label"),
                    "recommendationType": node.get("recommendationType"),
                    "status": node.get("status"),
                    "activityType": node.get("activityType"),
                    "interactionType": node.get("interactionType"),
                    "expectedOnly": node.get("expectedOnly"),
                    "sourceNodeId": node.get("sourceNodeId"),
                    "targetNodeId": node.get("targetNodeId"),
                    "canonicalSourceId": node.get("canonicalId"),
                    "explanation": node.get("explanation"),
                    "targetContext": node.get("targetContext"),
                    "analyticContrast": node.get("analyticContrast"),
                    "searchConcepts": node.get("searchConcepts"),
                    "decisionCriteria": node.get("decisionCriteria"),
                    "falsificationCriteria": node.get("falsificationCriteria"),
                }
            )
            if parent_instance_id is not None and relation_to_parent is not None:
                tree_edges.append(
                    {
                        "source": parent_instance_id,
                        "target": instance_id,
                        "relation": relation_to_parent,
                    }
                )

            child_entries = sorted(
                children_by_parent.get(canonical_id, []),
                key=lambda entry: (KIND_ORDER.get(nodes[entry[0]].get("kind", ""), 99), entry[0]),
            )
            for child_index, (child_id, relation) in enumerate(child_entries, start=1):
                visit(child_id, instance_id, relation, (*path, canonical_id), (*index_path, child_index))

        visit(root, None, None, tuple(), tuple())
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
        "sourceTrace": plan.get("trace"),
        "sourcePlanVersion": plan.get("version"),
        "trees": trees,
    }


def mermaid_id(instance_id: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", instance_id)


def mermaid_label(node: dict[str, Any]) -> str:
    parts = [str(node.get("kind") or "Node")]
    if node.get("recommendationType"):
        parts.append(str(node["recommendationType"]))
    if node.get("activityType"):
        parts.append(str(node["activityType"]))
    if node.get("interactionType"):
        parts.append(str(node["interactionType"]))
    if node.get("expectedOnly"):
        parts.append("Expected only")
    parts.append(str(node.get("label") or node["canonicalId"]))
    return "\\n".join(parts).replace("\\", "\\\\").replace('"', '\\"')


def markdown_cell(value: Any) -> str:
    if isinstance(value, list):
        return "<br>".join(markdown_cell(item) for item in value)
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def render_markdown(forest: dict[str, Any]) -> str:
    lines = [
        "# Recommendation Plan Forest",
        "",
        "This file is mechanically generated from `recommendation-plan-graph.json`. It is prescriptive: Expected Findings are plan targets, not evidence-backed Findings.",
        "",
    ]
    for tree_index, tree in enumerate(forest["trees"], start=1):
        lines.extend([f"## Tree {tree_index}: {tree['root']}", "", str(tree["rootLabel"]), ""])
        lines.extend(
            [
                "| Instance ID | Canonical ID | Parent | Relation | Kind | Recommendation Type | Status | Label |",
                "|---|---|---|---|---|---|---|---|",
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
                        node.get("recommendationType") or "",
                        node.get("status") or "",
                        node.get("label") or "",
                    ]
                )
                + " |"
            )
        strategy_nodes = [
            node
            for node in tree["nodes"]
            if node.get("kind") == "InvestigationStrategy"
            and any(
                node.get(field)
                for field in [
                    "explanation",
                    "targetContext",
                    "analyticContrast",
                    "searchConcepts",
                    "decisionCriteria",
                    "falsificationCriteria",
                ]
            )
        ]
        if strategy_nodes:
            lines.extend(
                [
                    "",
                    "### Strategy Context",
                    "",
                    "| Strategy | Explanation | Target Context | Analytic Contrast | Search Concepts | Decision Criteria | Falsification Criteria |",
                    "|---|---|---|---|---|---|---|",
                ]
            )
            for node in strategy_nodes:
                lines.append(
                    "| "
                    + " | ".join(
                        markdown_cell(value)
                        for value in [
                            node["canonicalId"],
                            node.get("explanation") or "",
                            node.get("targetContext") or "",
                            node.get("analyticContrast") or "",
                            node.get("searchConcepts") or "",
                            node.get("decisionCriteria") or "",
                            node.get("falsificationCriteria") or "",
                        ]
                    )
                    + " |"
                )
        lines.extend(["", "```mermaid", "flowchart TD"])
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
            "- Evidence Completion branches fill Reasoning Gaps under existing reasoning.",
            "- Hypothesis Expansion branches propose new Hypotheses from existing reasoning.",
            "- Expected Findings must be converted to real Findings only after follow-up evidence exists.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(forest: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_out.write_text(json.dumps(forest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(forest), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert recommendation-plan-graph.json into recommendation-plan-forest outputs."
    )
    parser.add_argument("plan", type=Path, help="Path to recommendation-plan-graph.json")
    parser.add_argument("--json-out", type=Path, help="Output path for recommendation-plan-forest.json")
    parser.add_argument("--md-out", type=Path, help="Output path for recommendation-plan-forest.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    json_out = args.json_out or args.plan.with_name("recommendation-plan-forest.json")
    md_out = args.md_out or args.plan.with_name("recommendation-plan-forest.md")
    try:
        plan = read_json(args.plan)
        nodes, edges, roots = validate_plan(plan)
        forest = build_forest(plan, nodes, edges, roots)
        write_outputs(forest, json_out, md_out)
    except PlanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {json_out}")
    print(f"wrote {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
