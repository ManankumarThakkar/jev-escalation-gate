# Decisions, and what they cost

## Why an answerability gate, and not routing or risk scoring

Three criteria: ground truth must not come from my own judgement, the task must
be legible to an engineer who has never used a decision model, and it must be a
real production step rather than a benchmark exercise.

Answerability satisfies all three. SQuAD 2.0 supplies the labels, "can this
passage answer this question" needs no explanation, and the pre-generation
gate is a step every retrieval system already has, usually without a gate in it.

Routing and risk scoring were rejected for the same reason: their ground truth
is a matter of opinion, so the experiment would have measured my labelling.

## Why three slices instead of a single accuracy number

Because a single number would have been 88% and meaningless. The whole finding
is that the figure swings 30.5 points depending on how the negatives are built,
and that is invisible unless the slices are scored separately.

The easy-negative slice also doubles as a contamination control, which a public
benchmark badly needs.

## Why no large-model baseline

No API access to a frontier model was available. Rather than fake one or quote
somebody else's benchmark as if it were ours, the comparison is stated for what
it is: Jev's confident slice against its uncertain slice. The README says so in
the limitations, and the post says so too.

This is the largest gap in the work. What would close it: running the identical
600 items through a small and a frontier chat model with the same instruction
text, and adding two columns.

## Why one question per request

Batching several questions into one call shares the state cost and is what
production code should do. It would also destroy the per-decision latency
measurement. Latency was under test, so the slower, more expensive shape was
used deliberately, and the cost figure is an upper bound.

## Why the ECE noise floor is resampled rather than assumed

A raw ECE of 0.047 reads like miscalibration until you know what a perfectly
calibrated model would score on the same 400 items. Simulating that 200 times
gives 0.039, which turns "0.047" into "1.2x the floor" and changes the
conclusion from "somewhat miscalibrated" to "about as calibrated as this sample
can demonstrate".

## Why the latency number is presented as an upper bound

A `jv_live_` key is issued by jevtypesafeai.com, a third-party metered proxy;
`api.typesafe.ai/v1/systemone` rejects it with a 401. Every call therefore
crossed a proxy. Reporting 662 ms p50 against a published 70-500 ms without
that caveat would be comparing two different things.

## What would have to change before production

1. Re-measure on real traffic. SQuAD passages are clean encyclopaedic prose;
   retrieved chunks are not.
2. Re-measure against the official endpoint with a TypeSafe key.
3. Decide the cost of each error direction. A false "answerable" produces a
   confident wrong answer; a false "unanswerable" spends a frontier call that
   was not needed. They are not equally bad, and the threshold should follow
   that asymmetry rather than sitting at 0.5.
4. Watch the band. If the escalated share drifts, either the traffic or the
   model has moved.
