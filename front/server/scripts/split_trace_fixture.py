#!/usr/bin/env python3
"""Split a ManiScope live-session trace into an initial trace and append payload."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
from pathlib import Path
from typing import Any


IMAGE_KEYS = {"imagePath", "sketchImagePath"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def iter_image_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in IMAGE_KEYS and isinstance(item, str):
                paths.append(item)
            else:
                paths.extend(iter_image_paths(item))
    elif isinstance(value, list):
        for item in value:
            paths.extend(iter_image_paths(item))
    return paths


def image_data_url(trace_dir: Path, image_path: str) -> str:
    source_path = trace_dir / image_path
    data = base64.b64encode(source_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def copy_referenced_images(trace_dir: Path, output_dir: Path, payload: dict[str, Any]) -> None:
    for image_path in sorted(set(iter_image_paths(payload))):
        source_path = trace_dir / image_path
        if not source_path.is_file():
            continue
        target_path = output_dir / image_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def append_image_map(trace_dir: Path, payload: dict[str, Any]) -> dict[str, str]:
    images: dict[str, str] = {}
    for image_path in sorted(set(iter_image_paths(payload))):
        source_path = trace_dir / image_path
        if source_path.is_file():
            images[image_path] = image_data_url(trace_dir, image_path)
    return images


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--action-cut", type=int, required=True, help="Number of actions to keep in part A.")
    parser.add_argument("--annotation-cut", type=int, help="Number of annotations to keep in part A. Defaults to half.")
    args = parser.parse_args()

    trace_dir = args.trace_dir.resolve()
    source_path = trace_dir / "session.json"
    source = load_json(source_path)
    actions = source.get("userActionSequence") or []
    annotations = source.get("annotationRecords") or []
    if not isinstance(actions, list) or not isinstance(annotations, list):
        raise SystemExit("session.json must contain userActionSequence and annotationRecords arrays")

    action_cut = min(max(args.action_cut, 0), len(actions))
    annotation_cut = args.annotation_cut
    if annotation_cut is None:
        annotation_cut = len(annotations) // 2
    annotation_cut = min(max(annotation_cut, 0), len(annotations))

    part_a = dict(source)
    part_a["userActionSequence"] = actions[:action_cut]
    part_a["annotationRecords"] = annotations[:annotation_cut]

    append_payload = {
        "coin": source.get("coin"),
        "annotationSeqId": source.get("annotationSeqId"),
        "snapshotCategories": (source.get("config") or {}).get("snapshotCategories"),
        "snapshotQuality": (source.get("config") or {}).get("snapshotQuality"),
        "userActionSequence": actions[action_cut:],
        "annotationRecords": annotations[annotation_cut:],
    }
    append_payload["images"] = append_image_map(trace_dir, append_payload)

    output_dir = args.output_dir.resolve()
    part_a_dir = output_dir / "part-a"
    write_json(part_a_dir / "session.json", part_a)
    copy_referenced_images(trace_dir, part_a_dir, part_a)
    write_json(output_dir / "part-b-append-import.json", append_payload)

    print(f"Wrote {part_a_dir / 'session.json'}")
    print(f"Wrote {output_dir / 'part-b-append-import.json'}")
    print(f"Part A actions/annotations: {len(part_a['userActionSequence'])}/{len(part_a['annotationRecords'])}")
    print(f"Part B actions/annotations: {len(append_payload['userActionSequence'])}/{len(append_payload['annotationRecords'])}")


if __name__ == "__main__":
    main()
