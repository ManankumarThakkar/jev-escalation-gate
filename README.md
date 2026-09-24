# 🚦 The Escalation Gate

**How much work can a small, cheap AI model take off an expensive one's plate, and how would you actually know?**

600 real decisions. 13 cents. Every number reproducible from this repo.

---

## 🎯 TL;DR

Three things came out of this, and the first one is the reason to read on:

1. **The same gate scored 100% and 69.5%** on the same model, same prompt, same afternoon. The only difference was how I built the wrong answers in the test set. Build your test the convenient way and you will ship something far worse than you measured.
2. **The confidence number is honest.** When the model said it was 97% sure, it was right 97.6% of the time.
3. **Because of #2, you can route on it** - but less dramatically than it first looks. A confident "this passage cannot answer it" lets you drop the passage before paying for generation: **14.5% of judgements**. A confident "it can" still needs the generation call. The gate decides *whether* to generate, not *what* to generate.

---

## 🧠 The problem, in plain English

Imagine a chatbot that answers questions about your company's documents. It works in two steps:

1. **Search** the documents and pull back the most relevant page.
2. **Ask a large AI model** to write an answer using that page.

Step 2 is the expensive one. It costs real money and takes real time, and here is the catch: **it runs whether or not the page actually contains the answer.**

When the search misses, you pay full price for the AI to write a confident, fluent, completely wrong answer from a page that never held the fact. That is the worst outcome available: expensive *and* misleading.

The obvious fix is a cheap bouncer at the door:

> "Before we spend the money, can this page even answer this question?"

That is a small, boring, repetitive judgement. It happens thousands of times a day. It is too fuzzy for a simple rule, and far too small to justify calling an expensive model every time.

**This repo tests whether a specialised small model can be that bouncer.**

---

## 🤔 What is Jev?

[Jev](https://jevtypesafeai.com/what-is-jev) is TypeSafe AI's "System One" model. The name borrows from psychology: System Two is slow, deliberate reasoning (what large language models do), System One is the fast, instinctive judgement you make without thinking.

The practical difference from a normal AI model:

| A normal LLM | Jev |
|---|---|
| Writes text back at you | Returns a **typed answer** your code can use directly |
| Can produce any shape, so you parse and pray | **Cannot** produce an invalid shape, ever |
| Seconds, cents | Sub-second, tiny fractions of a cent |
| Great at open-ended work | Built for small, repeated decisions |

You give it some context and a typed question, and it gives back one of three things:

- **choice** - pick one of up to 255 labelled options
- **score** - a rating on a scale you define
- **noul** - a yes/no as a probability from 0 to 1

That last one is what this experiment uses. And critically, TypeSafe claim those probabilities are **calibrated**: *"when Jev says it's 80% sure, it should be right about 80% of the time."*

That is a falsifiable claim. So I tested it.

---

## 🧪 What I actually did

**The task:** show the model a passage and a question, and ask for the probability that the passage contains what is needed to answer.

**The data:** 600 items from [SQuAD 2.0](https://rajpurkar.github.io/SQuAD-explorer/), a public reading-comprehension dataset. The correct answers come from the dataset and from how the items are constructed, never from my own opinion.

I split it into three groups of 200, and this split is where the interesting part came from:

| Group | What it is | Correct answer |
|---|---|---|
| ✅ **Answerable** | A question shown with the passage it was written from | yes |
| 😈 **Hard negative** | A question humans deliberately wrote to *look* answerable from that passage, but which it does not answer | no |
| 🙂 **Easy negative** | A real question shown a passage from a completely different article | no |

The easy group is a **cheating check**. SQuAD is a famous public dataset and may well be in the model's training data, which would make it look better than it is. The easy group pairs things that have never been paired before, so it cannot have been memorised.

---

## 📊 What happened

Model `jev-1.13.0`, 600 items, zero failures, **$0.127 total**.

### 1️⃣ The test set decided the score

| Group | Accuracy | What that means |
|---|---:|---|
| 🙂 Easy negative | **100.0%** | Perfect. Obviously unrelated pages are trivial to reject. |
| ✅ Answerable | 95.5% | Very good at spotting a page that genuinely answers. |
| 😈 Hard negative | **69.5%** | It waves through roughly 3 in 10 pages that look right but are silent on the fact. |

**That is a 30.5 point swing on one model, decided entirely by how I built the test.**

Here is why it matters: a real search miss does not look like a random page. It looks like a page that is *on topic and quietly missing the one fact you need*. That is the hard group. If I had built my test the easy way, I would have measured 100%, felt great, and shipped a bouncer that is actually 70%.

One nice detail on the cheating check: if memorisation were doing the work, the hard group (which *is* the public dataset) should be the easy one. It is not. The difficulty is real.

### 2️⃣ The confidence number is trustworthy

Over the realistic mix (answerable + hard negatives):

- Raw accuracy: **82.5%**
- Calibration error: **0.047**, against a **0.039** noise floor for this sample size

That second number matters. Even a *perfectly* calibrated model measured on 400
items would score about 0.039 from sampling noise alone, so 0.047 is close to
the floor rather than evidence of miscalibration.

But the aggregate flatters it, and this is worth being precise about:

| Confidence bucket | n | Stated | Observed | Gap |
|---|---:|---:|---:|---:|
| 0.95 - 1.00 | 164 | 0.974 | 0.976 | **+0.002** |
| 0.70 - 0.75 | 14 | 0.719 | 0.429 | **-0.290** |
| 0.65 - 0.70 | 13 | 0.672 | 0.462 | -0.211 |
| 0.55 - 0.60 | 19 | 0.572 | 0.368 | -0.203 |

The top bucket holds 164 of 400 items and is 86% easy positives, and it is
carrying the aggregate. The mid-range buckets are the least reliable, and they
are exactly where the escalation band sits.

So: **on this evaluation, high-confidence scores were dependable and mid-range
scores were not.** That is a measurement, not a validation. The thresholds were
chosen by reading this same data, so nothing here establishes that routing on
these scores would hold up in production.

### 3️⃣ Which means you can route on it

An answerability gate has three possible actions, and lumping them together is
how the saving gets overstated. Over the realistic mix (answerable + hard
negatives, n=400), at a band of 0.10 to 0.90:

| Score | Share | What it means | Composition |
|---|---:|---|---|
| **at or below 0.10** | **14.5%** | drop the passage, retrieve again. Avoids the generation call outright. | 57 hard negatives, **1 answerable wrongly dropped** |
| 0.10 to 0.90 | 42.5% | escalate the *judgement* to a stronger evaluator | 133 hard negatives, 37 answerable |
| at or above 0.90 | 43.0% | pass to answer generation. **Still costs an LLM call.** | 162 answerable, 10 hard negatives |

Two things worth pulling out of that table.

**The gate mostly declines to commit on the class it is worst at.** 133 of the
200 hard negatives land in the uncertain band. That is the behaviour you want
from a router, and it is more useful than any accuracy figure.

**10 hard negatives were accepted at 0.90 or above** — and reading them is what
corrected this write-up. At least 6 of those 10 have the answer plainly in the
passage; SQuAD labels them unanswerable and they are not. The model was right
and the benchmark was wrong.

So **69.5% is a floor, not an estimate**, and the earlier framing of those 10 as
"the production risk" was the same mistake this project is about. The genuine
errors cluster elsewhere, in a nameable shape. Case by case in
[docs/ADJUDICATION.md](docs/ADJUDICATION.md).

Rejecting a passage avoids the generation call outright. An escalated judgement
that comes back negative would avoid it too, but that second path was not
measured here, so **no end-to-end RAG saving is established**. This measures
answerability classification, not complete RAG requests.

All three shares are over the 400 answerable and hard-negative items. Over all
600, including the easy-negative control, the same band reads 42.8% rejected
rather than 14.5%, which is why the denominator has to be stated.

### 💵 Speed and cost, measured

| | Measured here | TypeSafe's published figure |
|---|---|---|
| Speed (median) | 662 ms | 70-500 ms |
| Cost per decision | $0.000212 | ~$0.0004 |

⚠️ **Do not read my speed number as contradicting theirs.** My calls went through a third-party proxy (see Limitations), so the measurement includes an extra network hop. Treat it as an upper bound.

---

## 💡 What you can take away

Useful even if you never touch Jev:

**🎯 Your benchmark can be wrong in both directions.** Convenient negatives flatter the model: 100% vs 69.5% on the same day, with test construction the only variable. Noisy labels punish it: at least 6 of the 10 most confident "failures" were not failures. Both were only visible by reading the cases one at a time.

**⚖️ A small model does not have to beat the big one to earn its place.** It has to be honest about when it is unsure. What made this useful was not its accuracy but where its uncertainty landed: mostly on the cases it was worst at.

**🔑 Calibration is the feature, not accuracy.** Everything useful here flows from the probability meaning what it says. Without that, there is no dial to turn and no gate to build.

---

## 👥 Who this is for

**Engineers building RAG or AI agents** - this is a working pattern you can lift: cheap gate in front, expensive model behind, threshold chosen from a measured curve instead of a guess.

**Anyone running up an AI bill** - the cheapest call is the one you do not make. This shows how to find out which calls those are, with evidence instead of vibes.

**Engineers who evaluate models** - the three-slice design (including a contamination control) is reusable for any classifier, and the resampled noise floor is worth stealing.

**Engineering leaders and recruiters** - the short version: this asks whether a cheap component can safely replace part of an expensive one, answers it with 600 measured decisions for 13 cents, finds the *measurement method* was the biggest lever, and states plainly what was not tested.

---

## ⚠️ Limitations

Stated up front, because a number whose limits are known is worth more than a better one that hides them.

- **One task, one dataset, one language.** Nothing here transfers to routing or risk scoring without re-measuring.
- **600 items.** Plenty for the group comparison, thin for the per-bucket calibration detail (13-20 items in some middle buckets).
- **A public benchmark.** SQuAD may be in training data. The easy-negative control addresses this but does not eliminate it.
- **Measured through a proxy.** A `jv_live_` key is issued by jevtypesafeai.com, a third-party metered proxy; the official `api.typesafe.ai` endpoint rejects it with a 401. Latency is an upper bound, not the model's own figure.
- **No large-model baseline.** 🚨 The biggest gap. I had no frontier-model API access, so this compares Jev's confident slice against its uncertain slice, **not** Jev against GPT or Claude. Nothing here says which is better.
- **One question per request.** Batching would lower the cost per decision.

The two pricing pages also disagree by 10x on the token rate ($0.042 vs $0.42 per million), so every cost figure here comes from what the API itself billed, not from either page.

---

## 🔁 Reproduce it

Python 3.11+. No third-party dependencies.

```bash
export JEV_API_KEY=...            # from whichever endpoint you use
python src/dataset.py --n 200     # rebuild the test set (seeded, deterministic)
python src/run_experiment.py      # ~7 minutes, ~$0.13
python src/analyze.py             # recompute every number above
```

Every raw response is committed in `results/`, so you can re-run the analysis without spending anything.

---

## 📁 What's in here

```
src/dataset.py          builds the three groups from SQuAD 2.0, seeded
src/jev.py              tiny Jev client, standard library only
src/run_experiment.py   one call per item, records speed/tokens/cost
src/analyze.py          accuracy, calibration, noise floor, coverage curve
results/raw-*.json      every single response, unedited
results/report.json     computed metrics
docs/DECISIONS.md       why this task, why three groups, why no baseline
docs/VERIFICATION.md    every published figure recomputed from the raw responses
docs/ADJUDICATION.md    all 61 false accepts read case by case, and what that changed
```

---

## 🔗 Sources

- [What is Jev](https://jevtypesafeai.com/what-is-jev)
- [Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [Building a harness with Jev (LangChain)](https://www.langchain.com/blog/building-a-harness-with-jev)
- [SQuAD 2.0](https://rajpurkar.github.io/SQuAD-explorer/)

Vendor performance figures are labelled as claims throughout. **Everything in the results section was measured by the code in this repository.**
