"""JSON exporter and deterministic side artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from data_generator.models import InstanceSpec, ValidationReport


def export(
    instance: dict[str, Any],
    spec: InstanceSpec,
    out_dir: str | Path,
    validation_report: ValidationReport | None = None,
    report_dir: str | Path | None = None,
) -> Path:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    instance_path = out_path / f"{spec.instance_name}.json"

    payload = json.dumps(instance, indent=2, ensure_ascii=False) + "\n"
    instance_path.write_text(payload, encoding="utf-8")

    if report_dir is None:
        report_path = out_path.parent / "validation_reports"
    else:
        report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    if spec.export.write_checksum:
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        (report_path / f"{spec.instance_name}.sha256").write_text(
            f"{digest}  {spec.instance_name}.json\n",
            encoding="utf-8",
        )

    if spec.export.write_summary:
        summary = _summary(instance)
        (report_path / f"{spec.instance_name}.summary.txt").write_text(
            summary,
            encoding="utf-8",
        )

    if spec.export.write_validation_report and validation_report is not None:
        report_payload = json.dumps(
            {
                "instance_name": spec.instance_name,
                "validation": validation_report.to_dict(),
                "baseline_feasible_routes": instance["baseline_feasible_routes"],
            },
            indent=2,
            ensure_ascii=False,
        )
        (report_path / f"{spec.instance_name}.validation.json").write_text(
            report_payload + "\n",
            encoding="utf-8",
        )

    return instance_path


def _summary(instance: dict[str, Any]) -> str:
    metadata = instance["metadata"]
    profile = instance["drone_profile"]
    routes = instance["baseline_feasible_routes"]
    return "\n".join(
        [
            f"instance_name: {metadata['instance_name']}",
            f"size_category: {metadata['size_category']}",
            f"random_seed: {metadata['random_seed']}",
            f"customers: {metadata['counts']['customers']}",
            f"no_fly_zones: {metadata['counts']['no_fly_zones']}",
            f"payload_capacity: {profile['payload_capacity']}",
            f"battery_capacity: {profile['battery_capacity']}",
            f"fleet_size: {profile['fleet_size']}",
            f"baseline_routes: {len(routes)}",
            "",
        ]
    )
