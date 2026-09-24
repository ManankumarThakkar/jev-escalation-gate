"""Ask Jev the answerability question once per item and record everything.

Deliberately one question per request, run sequentially. Batching several
questions into one call is cheaper and is what production code should do, but
it would make the per-decision latency figure meaningless, and latency is one
of the things under test. The cost figures are therefore an upper bound on what
a batched implementation would pay.

Raw per-item output is written before any analysis, so the numbers in
``results/`` can be recomputed without spending the API budget again.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jev import Jev, JevError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EVAL_SET = ROOT / "data" / "eval-set.json"
RESULTS = ROOT / "results"

# One instruction, identical for every item in every slice. Wording is fixed
# before the run: tuning it per slice would turn a measurement into a fit.
INSTRUCTIONS = (
    "Can this question be answered using only the information in the passage? "
    "Answer yes only if the passage actually contains the information needed. "
    "Answer no if the passage is about a different topic, or is on topic but "
    "does not state the specific fact the question asks for."
)


def build_state(item: dict) -> str:
    return f"PASSAGE:\n{item['context']}\n\nQUESTION:\n{item['question']}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="stop after N items (0 = all)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    data = json.loads(EVAL_SET.read_text())
    items = data["items"][: args.limit] if args.limit else data["items"]

    client = Jev()
    print(f"{len(items)} items | endpoint={'proxy' if client.via_proxy else 'official'}")

    rows, failures = [], 0
    started = time.time()
    for i, item in enumerate(items, 1):
        try:
            probability, meta = client.noul(build_state(item), INSTRUCTIONS)
        except JevError as exc:
            failures += 1
            print(f"  {i}/{len(items)} FAILED {exc}")
            continue
        rows.append({
            "item_id": item["item_id"], "slice": item["slice"],
            "answerable": item["answerable"], "squad_id": item["squad_id"],
            "p_answerable": probability, **meta,
        })
        if i % 50 == 0 or i == len(items):
            elapsed = time.time() - started
            print(f"  {i}/{len(items)}  {elapsed:.0f}s elapsed  "
                  f"${sum(r.get('cost_usd') or 0 for r in rows):.4f} spent")

    RESULTS.mkdir(exist_ok=True)
    out = Path(args.out) if args.out else RESULTS / f"raw-{time.strftime('%Y%m%dT%H%M', time.gmtime())}Z.json"
    out.write_text(json.dumps({
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint_is_proxy": client.via_proxy,
        "instructions": INSTRUCTIONS,
        "dataset": {k: data[k] for k in ("seed", "n_per_slice", "source")},
        "n_requested": len(items), "n_succeeded": len(rows), "n_failed": failures,
        "models_seen": sorted({r["model"] for r in rows if r.get("model")}),
        "total_cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 6),
        "wall_clock_s": round(time.time() - started, 1),
        "rows": rows,
    }, indent=2) + "\n")
    print(f"\nwrote {out}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
