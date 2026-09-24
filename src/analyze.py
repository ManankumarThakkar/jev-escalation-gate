"""Turn the raw run into the numbers the conclusion rests on.

Four things are computed, in the order they matter for an engineering decision:

1. **Accuracy per slice.** Headline accuracy over a mixed set hides which kind
   of negative the model actually handles, and that is the whole question.
2. **Calibration.** TypeSafe's stated goal is that "when Jev says it's 80%
   sure, it should be right about 80% of the time". That is a checkable claim,
   so it is checked - reliability bins plus expected calibration error, with a
   resampled noise floor so a small-sample ECE is not read as miscalibration.
3. **The coverage / accuracy curve.** The operational question: if uncertain
   cases escalate to an expensive model and confident ones are auto-handled,
   what fraction of traffic can be auto-handled, and how accurate is that
   fraction? This is what decides whether a hybrid architecture pays.
4. **Latency and cost**, measured, not quoted.
"""

import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def latest_raw() -> Path:
    files = sorted(RESULTS.glob("raw-*.json"))
    if not files:
        raise SystemExit("no raw results; run src/run_experiment.py first")
    return files[-1]


def confidence(p: float) -> float:
    """How sure the model is, regardless of which way it leaned."""
    return max(p, 1.0 - p)


def accuracy(rows: list[dict], threshold: float = 0.5) -> float | None:
    if not rows:
        return None
    correct = sum(1 for r in rows if (r["p_answerable"] >= threshold) == r["answerable"])
    return correct / len(rows)


def reliability(rows: list[dict], bins: int = 10) -> tuple[list[dict], float]:
    """Bin by confidence; compare stated confidence with observed accuracy."""
    edges = [0.5 + i * 0.5 / bins for i in range(bins + 1)]
    table, ece, total = [], 0.0, len(rows)
    for lo, hi in zip(edges, edges[1:]):
        chunk = [r for r in rows if lo <= confidence(r["p_answerable"]) < hi or
                 (hi == edges[-1] and confidence(r["p_answerable"]) == 1.0)]
        if not chunk:
            continue
        stated = statistics.fmean(confidence(r["p_answerable"]) for r in chunk)
        observed = accuracy(chunk)
        ece += len(chunk) / total * abs(stated - observed)
        table.append({"bin": f"{lo:.2f}-{hi:.2f}", "n": len(chunk),
                      "stated_confidence": round(stated, 4),
                      "observed_accuracy": round(observed, 4),
                      "gap": round(observed - stated, 4)})
    return table, ece


def ece_noise_floor(rows: list[dict], bins: int = 10, trials: int = 200, seed: int = 7) -> float:
    """What ECE a perfectly calibrated model would show at this sample size.

    Without this an ECE of 0.05 looks like miscalibration when it may just be
    what 600 items of sampling noise produces.
    """
    rng = random.Random(seed)
    floors = []
    for _ in range(trials):
        simulated = []
        for r in rows:
            c = confidence(r["p_answerable"])
            leaned_answerable = r["p_answerable"] >= 0.5
            correct = rng.random() < c
            truth = leaned_answerable if correct else not leaned_answerable
            simulated.append({"p_answerable": r["p_answerable"], "answerable": truth})
        floors.append(reliability(simulated, bins)[1])
    return statistics.fmean(floors)


def coverage_curve(rows: list[dict], steps: int = 21) -> list[dict]:
    """Auto-handle confident cases, escalate the uncertain band.

    A band half-width of w means: decide when p <= 0.5-w or p >= 0.5+w, and
    escalate otherwise. w = 0 auto-handles everything; larger w buys accuracy
    on the covered slice by sending more traffic to the expensive path.
    """
    out = []
    for i in range(steps):
        w = i * 0.5 / (steps - 1)
        covered = [r for r in rows if abs(r["p_answerable"] - 0.5) >= w]
        out.append({
            "band_half_width": round(w, 3),
            "escalate_if_between": [round(0.5 - w, 3), round(0.5 + w, 3)],
            "coverage": round(len(covered) / len(rows), 4),
            "n_covered": len(covered),
            "accuracy_on_covered": round(accuracy(covered), 4) if covered else None,
        })
    return out


def routing(rows: list[dict], lo: float = 0.10, hi: float = 0.90) -> dict:
    """The three actions an answerability gate can actually take.

    Separated deliberately, because "retained" conflates two different
    outcomes. A confident *unanswerable* lets you drop the passage before
    paying for generation. A confident *answerable* does not: the gate
    classifies, it does not generate, so that branch still costs a generation
    call. Reporting them as one number overstates the saving.
    """
    def bucket(pred):
        chunk = [r for r in rows if pred(r["p_answerable"])]
        by_slice: dict[str, dict[str, int]] = {}
        for r in chunk:
            entry = by_slice.setdefault(r["slice"], {"n": 0, "wrong": 0})
            entry["n"] += 1
            if (r["p_answerable"] >= 0.5) != r["answerable"]:
                entry["wrong"] += 1
        return {
            "n": len(chunk),
            "share": round(len(chunk) / len(rows), 4) if rows else None,
            "by_slice": by_slice,
        }

    return {
        "band": [lo, hi],
        "population": "answerable + hard_negative",
        "n": len(rows),
        "reject_confidently_unanswerable": {
            **bucket(lambda p: p <= lo),
            "action": "drop the passage or retrieve again; generation call avoided",
        },
        "escalate_uncertain": {
            **bucket(lambda p: lo < p < hi),
            "action": "escalate the answerability judgement to a stronger evaluator",
        },
        "accept_confidently_answerable": {
            **bucket(lambda p: p >= hi),
            "action": "pass to answer generation; this still costs a generation call",
        },
        "note": (
            "Thresholds were chosen by reading the coverage curve over these same "
            "items, so every share here is in-sample, not a validated estimate."
        ),
    }


def main() -> int:
    raw_path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_raw()
    raw = json.loads(raw_path.read_text())
    rows = raw["rows"]
    slices = sorted({r["slice"] for r in rows})

    per_slice = {}
    for s in slices:
        chunk = [r for r in rows if r["slice"] == s]
        per_slice[s] = {
            "n": len(chunk),
            "accuracy": round(accuracy(chunk), 4),
            "mean_p_answerable": round(statistics.fmean(r["p_answerable"] for r in chunk), 4),
            "median_p_answerable": round(statistics.median(r["p_answerable"] for r in chunk), 4),
        }

    # Realistic mix: answerable plus the hard negatives. The easy negatives are
    # a contamination control, not traffic anyone actually sees.
    realistic = [r for r in rows if r["slice"] in ("answerable", "hard_negative")]
    table, ece = reliability(realistic)
    floor = ece_noise_floor(realistic)
    lat = sorted(r["latency_ms"] for r in rows)
    toks = [r["input_tokens"] for r in rows if r.get("input_tokens")]

    report = {
        "source_run": raw_path.name,
        "endpoint_is_proxy": raw["endpoint_is_proxy"],
        "model": raw["models_seen"],
        "n": len(rows),
        "per_slice": per_slice,
        "realistic_mix": {
            "description": "answerable + hard_negative; excludes the easy-negative control",
            "n": len(realistic),
            "accuracy_at_0.5": round(accuracy(realistic), 4),
            "ece": round(ece, 4),
            "ece_noise_floor": round(floor, 4),
            "ece_over_floor": round(ece / floor, 2) if floor else None,
            "reliability_bins": table,
        },
        "coverage_curve_realistic": coverage_curve(realistic),
        "routing": routing(realistic),
        "latency_ms": {
            "p50": round(statistics.median(lat), 1),
            "p95": round(lat[int(len(lat) * 0.95)], 1),
            "p99": round(lat[int(len(lat) * 0.99)], 1),
            "note": "wall clock including a third-party proxy hop; not a server-side figure",
        },
        "cost": {
            "total_usd": raw["total_cost_usd"],
            "per_decision_usd": round(raw["total_cost_usd"] / len(rows), 7),
            "median_input_tokens": statistics.median(toks) if toks else None,
            "note": "one question per request; batching questions would lower this",
        },
    }

    out = RESULTS / "report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"model {report['model']}  n={report['n']}  (proxy={report['endpoint_is_proxy']})\n")
    print(f"{'slice':16} {'n':>4} {'accuracy':>9} {'mean p':>8} {'median p':>9}")
    for s, m in per_slice.items():
        print(f"{s:16} {m['n']:>4} {m['accuracy']:>9.3f} {m['mean_p_answerable']:>8.3f} "
              f"{m['median_p_answerable']:>9.3f}")

    rm = report["realistic_mix"]
    print(f"\nrealistic mix (answerable + hard negatives), n={rm['n']}")
    print(f"  accuracy @0.5   {rm['accuracy_at_0.5']:.3f}")
    print(f"  ECE             {rm['ece']:.3f}   (noise floor {rm['ece_noise_floor']:.3f}, "
          f"{rm['ece_over_floor']}x)")
    print("\n  stated conf -> observed accuracy")
    for b in rm["reliability_bins"]:
        print(f"    {b['bin']}  n={b['n']:>4}  stated {b['stated_confidence']:.3f}  "
              f"observed {b['observed_accuracy']:.3f}  gap {b['gap']:+.3f}")

    print("\ncoverage / accuracy trade (realistic mix)")
    print(f"  {'escalate band':>22} {'coverage':>9} {'acc on covered':>15}")
    for row in report["coverage_curve_realistic"]:
        if row["n_covered"] and round(row["band_half_width"] * 20) % 2 == 0:
            lo, hi = row["escalate_if_between"]
            print(f"  {f'{lo:.2f}-{hi:.2f}':>22} {row['coverage']:>9.3f} "
                  f"{row['accuracy_on_covered']:>15.3f}")

    rt = report["routing"]
    print(f"\nrouting at band {rt['band']}, {rt['population']}, n={rt['n']}")
    for key in ("reject_confidently_unanswerable", "escalate_uncertain",
                "accept_confidently_answerable"):
        b = rt[key]
        print(f"  {key:34} {b['n']:>4}  {b['share']*100:5.1f}%  {b['action']}")
        for sl, v in sorted(b["by_slice"].items()):
            print(f"      {sl:16} n={v['n']:>3} wrong={v['wrong']:>3}")

    print(f"\nlatency p50/p95/p99: {report['latency_ms']['p50']:.0f} / "
          f"{report['latency_ms']['p95']:.0f} / {report['latency_ms']['p99']:.0f} ms (via proxy)")
    print(f"cost: ${report['cost']['total_usd']:.4f} total, "
          f"${report['cost']['per_decision_usd']:.7f} per decision, "
          f"median {report['cost']['median_input_tokens']} input tokens")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
