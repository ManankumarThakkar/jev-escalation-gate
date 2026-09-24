# Reading all 61 false accepts

The gate called 61 of the 200 hard negatives answerable. The first version of
this write-up reported the 10 highest-confidence of those as "confident
failures" and called them the production risk. That was wrong, and reading them
is what showed it.

**Method and its limit.** I read all 61 myself, question and passage side by
side, asking one thing: does this passage contain the information needed to
answer this question as asked? This is a single reader with knowledge of what
the model said, which is exactly the weakness this project criticises elsewhere.
It is a re-reading, not an independent re-labelling, and the counts below should
be read as "one careful reader's view", not as ground truth.

## What the highest-confidence accepts actually are

Of the 10 scored at 0.90 or above, **at least 6 have the answer plainly in the
passage**. SQuAD 2.0 marks them unanswerable; they are not.

| Score | Question | The passage says |
|---:|---|---|
| 0.99 | How many **stories** does the Bank of America tower have? | "includes **42 floors**" |
| 0.98 | What was sold to foreign PTTs? | "Northern Telecom **sold several DATAPAC clones to foreign PTTs**" |
| 0.97 | Health problems were higher in places with higher levels of what? | "...higher rates of health and social problems ... in countries and states with **higher inequality**" |
| 0.95 | How many electorates does the Legislative Council have? | "divided into **eight electorates**" |
| 0.93 | Who presented briefing B-265 to the US Air Force? | "**Baran** ... first presented to the Air Force ... as briefing B-265" |
| 0.92 | What was the source of the Rhine during the last Ice Age? | "its source must still have been **a glacier**" |

The model was right and the benchmark was wrong. Reported as a model failure,
this would have been the same error the rest of this project is about.

## What the genuine errors look like

The remaining accepts, and nearly all of the 51 scored between 0.50 and 0.90,
are real mistakes. They share a shape. SQuAD 2.0 builds unanswerable questions
by perturbing an answerable one, and the gate is weak at detecting exactly those
perturbations:

| Perturbation | Example | Passage |
|---|---|---|
| **Name swap** | "developed by Carl von **Hampson** and William **Linde**" | "Carl von **Linde** and British engineer William **Hampson**" |
| **Entity swap** | "**Who** presented..." vs who received | "When Corliss **was given** the Rumford medal" |
| **Negation** | "What **is** fully understood about γδ T cells?" | "...are **not** fully understood" |
| **Negation** | "What **are** intended as a practical computing technology?" | "Turing machines are **not** intended as..." |
| **False premise** | "What success did Abercrombie gain out of the **win** at Carillon?" | Carillon was Abercrombie's **defeat** |
| **Numeric alteration** | "a gas stream that is **9%** to 93% O2" | "**90%** to 93%" |
| **Wrong agent** | "What areas did the **English** recruit natives from?" | "the **French** used their trading connections to recruit" |

## The finding this changes

Confidence and label quality move together, in the direction that flatters the
model rather than the benchmark:

- **At 0.90 and above**, most of the "errors" are the benchmark's.
- **Between 0.50 and 0.90**, the errors are real and are overwhelmingly these
  perturbation traps.

So the measured 69.5% on hard negatives is a **floor, not an estimate**. Some
unknown share of the 61 are label noise, and correcting them would raise it.

It also names the weakness usefully. The gate handles topic mismatch almost
perfectly. What it misses is a question that has been subtly altered relative to
the passage: a swapped name, an inverted claim, a changed number. If you are
gating retrieval, that is the failure mode to probe, and it will not show up in
a test set built from random pairings.

## What would settle it

Independent re-labelling by someone who has not seen the model's scores, on a
random sample of the 61, with the disagreement rate against SQuAD reported.
That is the honest version of this document and it has not been done.
