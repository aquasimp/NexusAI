"""CLI: `python -m nexus.eval.runner [--seeds N] [--clean N] [--quick]`"""
from __future__ import annotations
import argparse, json, sys

from .. import store
from ..config import settings
from . import benchmark


def main() -> int:
    ap = argparse.ArgumentParser(description="NEXUS AI benchmark harness")
    ap.add_argument("--seeds", type=int, default=settings.eval_seeds_per_scenario)
    ap.add_argument("--clean", type=int, default=settings.eval_clean_episodes)
    ap.add_argument("--quick", action="store_true", help="3 seeds, 6 clean (smoke)")
    a = ap.parse_args()
    seeds, clean = (3, 6) if a.quick else (a.seeds, a.clean)

    def prog(kind, data):
        if kind == "episode":
            print(f"\r  episodes {data['done']}/{data['total']} "
                  f"({data['scenario']})".ljust(64), end="", file=sys.stderr)
        else:
            print(f"[{kind}] {json.dumps(data)}", file=sys.stderr)

    print(f"Running benchmark: {seeds} seeds x 7 scenarios + {clean} clean episodes",
          file=sys.stderr)
    run = benchmark.run(seeds, clean, prog)
    print(file=sys.stderr)
    store.init()
    store.save_eval(run)
    d, r = run["detection"], run["root_cause"]
    print(f"\nDetection    F1={d['f1']}  recall={d['recall']} "
          f"(CI {d['recall_ci95']})  FP/clean-ep={d['false_positive_rate_per_clean_episode']}")
    print(f"Localization top1={run['localization']['top1_accuracy']} "
          f"top3={run['localization']['top3_accuracy']}")
    print(f"Root cause   learned={r.get('learned_accuracy')} "
          f"macroF1={r.get('macro_f1')}  rule={r['rule_baseline_accuracy']}")
    print(f"Retrieval    {run['retrieval']['predicted_class_query']}")
    print(f"Joint        {run['investigation']['joint_success_rate']} "
          f"(CI {run['investigation']['joint_success_ci95']})")
    print(f"\nWritten -> {settings.eval_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
