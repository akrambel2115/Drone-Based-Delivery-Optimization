"""Regenerate one benchmark instance."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_generator.config_loader import load_spec
from data_generator.exporter import export
from data_generator.instance_builder import build_instance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance_config", type=Path)
    parser.add_argument("--master", type=Path, default=ROOT / "configs" / "master_config.json")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data" / "instances")
    parser.add_argument(
        "--report-dir", type=Path, default=ROOT / "data" / "validation_reports"
    )
    args = parser.parse_args()

    config_path = args.instance_config
    if not config_path.is_absolute():
        config_path = ROOT / config_path

    spec = load_spec(args.master, config_path)
    instance, report = build_instance(spec)
    output = export(instance, spec, args.out_dir, report, args.report_dir)
    print(f"generated {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
