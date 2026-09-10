"""Administrative DEMO commands with explicit local-only safety gates."""

import argparse
import json
import os
import sys

from app.demo.safety import LOCAL_DEMO_CONFIRMATION, DemoSafetyError, validate_demo_target


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default error echoes rejected arguments, which may contain a DSN.
        print(json.dumps({"code": "DEMO_COMMAND_INVALID"}), file=sys.stderr)
        raise SystemExit(2)


def main() -> int:
    parser = SafeArgumentParser(description="Market Pulse local DEMO administration")
    parser.add_argument(
        "command",
        choices=("check-target", "validate-data", "bootstrap_demo", "seed_demo", "reset_demo"),
    )
    args = parser.parse_args()
    if args.command == "validate-data":
        from app.demo.dataset import build_demo_dataset

        summary = build_demo_dataset().summary()
        print(
            json.dumps(
                {
                    "status": "OFFLINE_DATASET_ONLY",
                    "writes_performed": False,
                    "persistence_gate": "NOT_RUN",
                    "data_level": "DEMO",
                    "cutoff": summary["cutoff"],
                    "fingerprint": summary["fingerprint"],
                    "counts": {
                        key: value for key, value in summary.items() if isinstance(value, int)
                    },
                }
            )
        )
        return 0
    try:
        target = validate_demo_target(os.environ, confirmation=LOCAL_DEMO_CONFIRMATION)
        if args.command == "bootstrap_demo":
            from app.demo.operations import bootstrap_demo

            print(json.dumps(bootstrap_demo()))
            return 0
        if args.command == "seed_demo":
            from app.demo.operations import seed_demo

            print(json.dumps(seed_demo()))
            return 0
        if args.command == "reset_demo":
            from app.demo.operations import reset_demo

            print(json.dumps(reset_demo()))
            return 0
    except DemoSafetyError:
        print(
            json.dumps({"code": "DEMO_TARGET_DENIED"}),
            file=sys.stderr,
        )
        return 2
    except Exception:
        print(json.dumps({"code": "DEMO_OPERATION_FAILED"}), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "CONFIGURATION_ONLY",
                "database": target.database,
                "environment": target.environment,
                "database_connected": False,
                "writes_performed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
