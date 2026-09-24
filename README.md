# Can a small judgment model own part of your traffic?

An independent experiment with **Jev**, TypeSafe AI's System One model, on one
narrow question: *how much work can a fast, cheap, calibrated decision model
take off an expensive model's plate, and how would you know?*

600 real decisions, $0.127, reproducible from this repository.

---

## The problem this is about

A retrieval-augmented system does this constantly:

1. A user asks something.
2. Retrieval returns a passage.
3. A large model is called to generate an answer from that passage.

Step 3 is the expensive step, and it runs whether or not the passage can
actually answer the question. When retrieval misses, you pay full price to
generate a confident-sounding answer from a passage that never contained the
fact — the worst outcome available.

The obvious fix is a cheap gate in front of step 3: *can this passage answer
this question at all?* That is a small, repetitive, high-volume judgement. It
is exactly what a System One model claims to be for.

The interesting engineering question is not whether Jev is as good as a large
model. It is **whether it knows when it is unsure**, because that is what lets
you give it a slice of traffic and escalate the rest.

## What Jev is, briefly

Jev takes a `state` (any text) and typed `questions`, and returns typed answers
rather than prose. Three primitives: `choice` (one of up to 255 labelled
options), `score` (an ordered scale), and `noul` (a yes/no as a probability
from 0 to 1). It cannot return a malformed answer, because the shape is fixed
by the request.

TypeSafe trained it with RLCD — Reinforcement Learning for Calibrated Decisions
— and state the goal plainly: *"when Jev says it's 80% sure, it should be right
about 80% of the time."* That is a falsifiable claim, so this repository checks
it.

This experiment uses one `noul` question per item.

## The experiment

**Task.** Answerability gating. Given a passage and a question, return the
probability that the passage contains the information needed to answer it.

**Data.** [SQuAD 2.0 dev](https://rajpurkar.github.io/SQuAD-explorer/), 600
items in three slices of 200. Ground truth comes from the dataset and from
construction, not from a model and not from my own judgement:

| Slice | How it is built | Correct answer |
|---|---|---|
| `answerable` | A question paired with the passage it was written from | yes |
| `hard_negative` | SQuAD 2.0's own unanswerable questions — written by humans to *look* answerable from that passage | no |
| `easy_negative` | A real question paired with a passage from a different article | no |

The third slice is a **contamination control**. SQuAD 2.0 is public and may be
in the model's training data, which would flatter the first two slices. The
cross-paired negatives are combinations that have never existed before, so they
cannot have been memorised.

**Method.** One question per request, sequential, identical instruction text
for every item, fixed before the run. Batching questions into one call would be
cheaper and is what production code should do; it would also make per-decision
latency meaningless, and latency is under test.

## Results

Model `jev-1.13.0`, 600 items, 0 failures, **$0.127 total**.

### Accuracy depends almost entirely on how the negatives were made

| Slice | n | Accuracy | Mean p(answerable) |
|---|---:|---:|---:|
| `easy_negative` | 200 | **1.000** | 0.023 |
| `answerable` | 200 | 0.955 | 0.912 |
| `hard_negative` | 200 | **0.695** | 0.339 |

A **30-point gap** between the two kinds of negative. On passages that are
obviously unrelated, the gate is perfect and extremely confident. On passages
that are on-topic but do not contain the fact — which is what a retrieval miss
actually looks like — it says "yes, answerable" about three times in ten.

Note the direction of the contamination argument: if memorisation were doing
the work, the hard negatives (which *are* in the public dataset) should be the
easy ones. They are not. The difficulty is real.

### Calibration holds

Over the realistic mix (`answerable` + `hard_negative`, n=400):

- Accuracy at a 0.5 threshold: **0.825**
- Expected calibration error: **0.047**
- ECE noise floor at this sample size: **0.039** → measured ECE is **1.2×** the floor

A perfectly calibrated model measured on 400 items would show about 0.039 by
sampling noise alone, so 0.047 is close to as good as this sample can
demonstrate. The claim survives the test.

Where it matters most, it is very good. The highest-confidence bin:

| Stated confidence | n | Observed accuracy | Gap |
|---|---:|---:|---:|
| 0.95 – 1.00 | 164 | 0.976 | **+0.002** |

The middle bins are noisier and lean over-confident (the 0.70–0.75 bin observes
0.429 against a stated 0.719), but each holds only 13–20 items, which is too
few to conclude much.

### The number that decides the architecture

Auto-handle a decision when the probability is outside an escalation band;
send the rest to a large model.

| Escalate when p is between | Coverage | Accuracy on covered |
|---|---:|---:|
| — (auto-handle everything) | 100% | 0.825 |
| 0.30 – 0.70 | 83.3% | 0.889 |
| 0.20 – 0.80 | 75.5% | 0.920 |
| **0.10 – 0.90** | **57.5%** | **0.952** |
| 0.07 – 0.93 | 50.7% | 0.966 |
| 0.03 – 0.97 | 24.0% | 0.979 |

**Roughly 6 decisions in 10 can be made at 95% accuracy for about two
hundredths of a cent each**, with the remaining 4 escalated. That is the
practical result, and it exists only because the confidence number means
something — an uncalibrated model would give you a coverage knob that does not
buy accuracy.

### Measured latency and cost

| | Measured here | TypeSafe's published figure |
|---|---|---|
| Latency p50 / p95 / p99 | 662 / 823 / 1754 ms | 70–500 ms |
| Cost per decision | $0.000212 | ≈ $0.0004 |
| Median input tokens per request | 488 | — |

The latency figures are **not comparable** to the published ones and should not
be read as contradicting them: these calls went through
`jevtypesafeai.com`, a third-party metered proxy, because a `jv_live_` key is
a proxy credential and the official `api.typesafe.ai/v1/systemone` endpoint
rejects it with a 401. The measurement includes a proxy hop and public internet
from a single location. Set `JEV_ENDPOINT` to the official URL with a TypeSafe
key to measure the model rather than the path to it.

Two pricing pages disagree by 10× on the per-token rate ($0.042 vs $0.42 per
million input tokens), so the cost above is taken from the `usage.cost_usd`
the API itself returned on each call rather than from either page.

## What I would take from this

**Test your gate with hard negatives or you will ship the wrong number.** The
same model, same prompt, same day scored 100% and 69.5% depending only on how
the negative cases were constructed. A benchmark built from random pairings
would have told me this gate was flawless.

**A small model does not have to be as good as a large one to be worth
deploying.** It has to be honest about its uncertainty. 82.5% accuracy sounds
mediocre; 95.2% on 57.5% of traffic is an architecture.

**Calibration is the feature, not the accuracy.** Everything useful here comes
from the probability meaning what it says. If it did not, the coverage curve
would be flat and there would be no gate to build.

## Limitations

- **One task, one dataset, one language.** Answerability over English
  Wikipedia. Nothing here generalises to routing, ranking, or risk scoring
  without re-measuring.
- **600 items.** Enough for the slice gap, thin for the per-bin calibration
  figures (13–20 items in the middle bins).
- **A public benchmark.** SQuAD 2.0 may be in training data. The easy-negative
  control addresses this, but does not eliminate it.
- **Measured through a proxy**, so latency is an upper bound and is not the
  model's own figure.
- **No large-model baseline.** I did not have API access to a frontier model,
  so this does not show what a large model would score on the same items. The
  comparison here is between Jev's confident slice and its uncertain slice —
  not between Jev and anything else.
- **One question per request.** Batching would lower cost per decision.

## Reproduce it

Python 3.11+, no third-party dependencies.

```bash
export JEV_API_KEY=...            # get one from the endpoint you intend to use
python src/dataset.py --n 200     # rebuild the eval set (seeded, deterministic)
python src/run_experiment.py      # ~7 minutes, ~$0.13
python src/analyze.py             # recompute every number in this README
```

`results/raw-*.json` holds every per-item response, so the analysis can be
re-run without spending the API budget again.

## Layout

```
src/dataset.py         build the three slices from SQuAD 2.0, seeded
src/jev.py             minimal stdlib Jev client
src/run_experiment.py  one call per item, records latency/tokens/cost
src/analyze.py         accuracy, calibration, coverage curve, ECE noise floor
results/raw-*.json     every raw response
results/report.json    computed metrics
linkedin/              post copy and the figure
```

## Sources

- [What is Jev](https://jevtypesafeai.com/what-is-jev)
- [Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [Building a harness with Jev (LangChain)](https://www.langchain.com/blog/building-a-harness-with-jev)
- [SQuAD 2.0](https://rajpurkar.github.io/SQuAD-explorer/)

Vendor performance figures above are labelled as claims. Everything in the
Results section was measured by the code in this repository.
