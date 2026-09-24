"""Build three evaluation slices from SQuAD 2.0, with ground truth by construction.

The task is an **answerability gate**: given a retrieved passage and a user
question, can the passage support an answer at all? In a retrieval-augmented
system this is the cheap check you would run before spending a large
generation call on context that cannot answer the question.

Three slices, because "can it tell answerable from unanswerable?" is a
different question depending on how the unanswerable cases were made:

* ``answerable``      - a question paired with the passage it was written from.
* ``hard_negative``   - SQuAD 2.0's own unanswerable questions, written by
                        humans to look answerable from the passage. This is the
                        case that matters in production: retrieval returned
                        something topically right but factually silent.
* ``easy_negative``   - an answerable question paired with a passage from a
                        different article. Trivially unrelated.

The easy slice exists as a contamination control. SQuAD 2.0 is a public
benchmark and may well be in the model's training data, which would flatter the
first two slices. The cross-paired negatives are novel combinations that cannot
have been memorised, so a large gap between the two negative slices tells us
something the headline accuracy does not.

Sampling is seeded, so the same command reproduces the same set.
"""

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQUAD = ROOT / "data" / "squad2-dev.json"
OUT = ROOT / "data" / "eval-set.json"

# Passages shorter than this tend to be fragments; longer ones cost tokens
# without changing the judgement. Both bounds are stated so the sample can be
# reproduced or deliberately changed.
MIN_CHARS, MAX_CHARS = 400, 2200


def load_paragraphs() -> list[dict]:
    data = json.loads(SQUAD.read_text())["data"]
    out = []
    for article in data:
        for para in article["paragraphs"]:
            if MIN_CHARS <= len(para["context"]) <= MAX_CHARS:
                out.append({"article": article["title"], "context": para["context"], "qas": para["qas"]})
    return out


def build(n_per_slice: int, seed: int) -> dict:
    rng = random.Random(seed)
    paras = load_paragraphs()
    rng.shuffle(paras)

    answerable, hard, easy = [], [], []

    for para in paras:
        pos = [q for q in para["qas"] if not q.get("is_impossible")]
        neg = [q for q in para["qas"] if q.get("is_impossible")]

        if pos and len(answerable) < n_per_slice:
            q = rng.choice(pos)
            answerable.append({
                "slice": "answerable", "answerable": True,
                "question": q["question"].strip(), "context": para["context"],
                "source_article": para["article"], "squad_id": q["id"],
            })
        if neg and len(hard) < n_per_slice:
            q = rng.choice(neg)
            hard.append({
                "slice": "hard_negative", "answerable": False,
                "question": q["question"].strip(), "context": para["context"],
                "source_article": para["article"], "squad_id": q["id"],
            })

    # Cross-pair for the easy negatives: a real answerable question, but shown a
    # passage from a different article, so the correct answer is unambiguously
    # "no". Rejecting same-article pairs matters - two paragraphs of one article
    # often do contain each other's answers, which would silently mislabel.
    pool = [p for p in paras if any(not q.get("is_impossible") for q in p["qas"])]
    while len(easy) < n_per_slice and len(pool) > 1:
        qp, cp = rng.sample(pool, 2)
        if qp["article"] == cp["article"]:
            continue
        q = rng.choice([x for x in qp["qas"] if not x.get("is_impossible")])
        easy.append({
            "slice": "easy_negative", "answerable": False,
            "question": q["question"].strip(), "context": cp["context"],
            "source_article": f"{qp['article']} question over {cp['article']} passage",
            "squad_id": q["id"],
        })

    items = answerable + hard + easy
    for i, item in enumerate(items):
        item["item_id"] = f"{item['slice']}-{i:04d}"
    rng.shuffle(items)
    return {"seed": seed, "n_per_slice": n_per_slice,
            "source": "SQuAD 2.0 dev (rajpurkar.github.io)", "items": items}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200, help="items per slice")
    ap.add_argument("--seed", type=int, default=20260924)
    args = ap.parse_args()

    built = build(args.n, args.seed)
    OUT.write_text(json.dumps(built, indent=2) + "\n")

    counts: dict[str, int] = {}
    for item in built["items"]:
        counts[item["slice"]] = counts.get(item["slice"], 0) + 1
    print(f"{len(built['items'])} items -> {OUT}")
    for k, v in sorted(counts.items()):
        print(f"  {k:16} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
