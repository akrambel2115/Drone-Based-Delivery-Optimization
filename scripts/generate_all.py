"""Regenerate all 10 benchmark instances."""

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
    parser.add_argument("--configs-dir", type=Path, default=ROOT / "configs")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data" / "instances")
    parser.add_argument(
        "--report-dir", type=Path, default=ROOT / "data" / "validation_reports"
    )
    parser.add_argument("--no-clean", action="store_true", help="Do not remove old outputs first")
    args = parser.parse_args()

    master = args.configs_dir / "master_config.json"
    instance_configs = sorted(args.configs_dir.glob("instance_*.json"))
    if len(instance_configs) != 10:
        raise SystemExit(f"Expected 10 instance configs, found {len(instance_configs)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_clean:
        for path in args.out_dir.glob("*.json"):
            path.unlink()
        for path in args.report_dir.glob("*"):
            if path.is_file():
                path.unlink()

    generated = []
    for config_path in instance_configs:
        spec = load_spec(master, config_path)
        instance, report = build_instance(spec)
        output = export(instance, spec, args.out_dir, report, args.report_dir)
        generated.append(output)
        print(f"generated {output.relative_to(ROOT)}")

    print(f"done: {len(generated)} instances")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
