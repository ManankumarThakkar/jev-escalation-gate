# Verification against raw data

Every figure recomputed from `results/raw-20260924T1549Z.json` in
`ManankumarThakkar/jev-escalation-gate`, not from the README, the previous post,
or the previous image. Design facts read from `src/run_experiment.py`,
`src/dataset.py` and `src/analyze.py`.

## Confirmed as stated

| Claim | Verified | Source |
|---|---|---|
| 600 requested, 600 succeeded, 0 failed, 0 exclusions | yes | raw `n_requested`/`n_succeeded`/`n_failed` |
| Model `jev-1.13.0` | yes | raw `models_seen` |
| Total cost $0.127017, $0.0002117 per decision | yes, sum of per-call `cost_usd` matches the reported total exactly | raw rows |
| Easy negative 100% | **200/200** | recomputed |
| Answerable 95.5% | **191/200** | recomputed |
| Hard negative 69.5% | **139/200** | recomputed |
| 30.5 point gap | yes (100.0 - 69.5) | recomputed |
| Latency p50 662 ms, p95 823, p99 1754 | yes | raw `latency_ms` |
| Median 488 input tokens (min 400, max 774) | yes | raw rows |
| One instruction string, identical across all three slices | yes | `run_experiment.py` INSTRUCTIONS |
| One question per request, sequential | yes | `run_experiment.py` loop |
| Seeded sample, 200 per slice, seed 20260924 | yes | `dataset.py` |

## Corrections required

**1. "57.5% of traffic" did not say which traffic.**
The coverage curve was computed over the 400-item realistic mix
(answerable + hard_negative), excluding the easy-negative control. 57.5% of 400
is 230 retained, 219 correct = 95.2%. The arithmetic is right; the population
was never stated. Over all 600 the same band retains 71.5% at 97.4%, so the
unqualified figure is ambiguous.

**2. "95.2% accuracy on retained" hides where the errors are.**
Of the 11 errors in the retained set, **10 are hard negatives confidently
accepted at p >= 0.90** and 1 is an answerable passage wrongly dropped. A
headline of 95.2% conceals that the residual error is almost entirely the
dangerous direction: unanswerable passages waved through with high confidence.
That is 10/200 = **5.0% of all hard negatives**.

**3. The architecture claim was wrong.**
The previous image said a confident answerable verdict meant "answer it
yourself, no big model". An answerability gate classifies; it does not generate.
A confident *answerable* still requires the generation call. The call is only
avoided on the confident *unanswerable* path.

Correct three-way split on the realistic mix (n=400):

| Band | n | % | Composition | Action |
|---|---:|---:|---|---|
| p <= 0.10 | 58 | 14.5% | 57 hard neg, 1 answerable | drop / re-retrieve. **Generation call avoided.** |
| 0.10 < p < 0.90 | 170 | 42.5% | 133 hard neg, 37 answerable | escalate the judgement |
| p >= 0.90 | 172 | 43.0% | 162 answerable, 10 hard neg | pass to generation. **Still an LLM call.** |

So the share of judgements that avoid a generation call is **14.5%**, not 57.5%.

**4. "Jev's probabilities are calibrated" is overstated.**
Aggregate ECE 0.0467 against a resampled noise floor of 0.0388 (1.2x). But that
aggregate is carried by one large, easy bin: the 0.95-1.00 bucket holds 164 of
400 items and is 86% answerable (141 answerable, 23 hard negative). The
mid-range buckets are the least reliable, with gaps of -0.203 (0.55-0.60),
-0.211 (0.65-0.70) and -0.290 (0.70-0.75) on 13-19 items each. Those buckets are
exactly where the escalation band sits.

**5. "97% sure, right 97.6%" is one bucket.**
True, but it is the top bucket only (n=164 of 400) and dominated by the easy
positive class. All 4 of its errors are hard negatives. Keep only with scope.

**6. Thresholds are in-sample.**
`analyze.py` sweeps 21 bands over the same 400 items; 0.10/0.90 was chosen by
reading that curve. The retained figures are an in-sample observation, not a
validated production estimate.

**7. The 100% needs a baseline caveat.**
A trivial classifier that always answers "unanswerable" also scores 100% on both
negative slices, and 0% on answerable. Category accuracy alone does not
establish discrimination.

## Not verifiable / out of scope

- **No frontier-model baseline.** None was run. Nothing here supports any claim
  about Jev versus GPT, Claude or any other model.
- **Latency is proxy-inclusive.** Calls went through jevtypesafeai.com. This is
  a measurement of a path, not of the model, and it is not a strict upper bound
  on direct API latency either, since a different network path could be slower.
- **No end-to-end RAG cost measurement.** Only classification cost was measured.
- **Contamination not ruled out.** SQuAD 2.0 is public. The cross-paired easy
  negatives are novel combinations, but that does not rule out memorisation of
  the underlying passages or questions.

## Repository README

The repo README still carries framings 1, 2 and 4 above. Worth correcting before
the post drives traffic to it.
