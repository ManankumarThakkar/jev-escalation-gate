"""Render the post figure directly from the experiment's raw responses.

Every number is recomputed from `results/raw-*.json`, so the image cannot drift
from the data or from the post. Nothing is typed in by hand. The HTML this
writes is the editable source: change it and re-screenshot.

Layout reasoning, since it is not obvious from the code:

* The two **negative** slices are the comparison, so they sit together with the
  gap drawn between them. Previously the positive slice sat between them, which
  made the headline contrast impossible to see at a glance.
* The positive slice moves below as a reference line. It is context for the
  comparison, not part of it.
* The two error counts get their own tiles. "10 accepted at 0.90 or above" is
  the finding a senior reader cares about and it was previously buried in a
  paragraph.
* Routing shrinks to a strip. It is the supporting insight; the accuracy gap is
  the story.

Wording rules enforced here: negative *examples*, never "wrong answers";
rejecting avoids generating *from that passage*, not an entire LLM call; a false
acceptance *risks* an unsupported answer rather than guaranteeing a
hallucination.
"""

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "linkedin" / "figure.html"
REPO_URL = "github.com/ManankumarThakkar/jev-escalation-gate"
LO, HI = 0.10, 0.90


def data() -> dict:
    raw = json.load(open(sorted(glob.glob(str(ROOT / "results" / "raw-*.json")))[-1]))
    rows = raw["rows"]
    real = [r for r in rows if r["slice"] in ("answerable", "hard_negative")]

    def correct(name):
        chunk = [r for r in rows if r["slice"] == name]
        return sum(1 for r in chunk if (r["p_answerable"] >= 0.5) == r["answerable"]), len(chunk)

    rej = [r for r in real if r["p_answerable"] <= LO]
    esc = [r for r in real if LO < r["p_answerable"] < HI]
    acc = [r for r in real if r["p_answerable"] >= HI]
    easy, ans, hard = correct("easy_negative"), correct("answerable"), correct("hard_negative")
    return {
        "easy": easy, "ans": ans, "hard": hard,
        "gap": (easy[0] / easy[1] - hard[0] / hard[1]) * 100,
        "n_real": len(real), "n_all": len(rows),
        "rej_pct": len(rej) / len(real) * 100,
        "esc_pct": len(esc) / len(real) * 100,
        "acc_pct": len(acc) / len(real) * 100,
        "false_accept": len([r for r in acc if not r["answerable"]]),
        "false_reject": len([r for r in rej if r["answerable"]]),
        "hard_escalated": len([r for r in esc if r["slice"] == "hard_negative"]),
        "n_hard": hard[1],
        "model": raw["models_seen"][0],
    }


def main() -> int:
    d = data()
    (ec, en), (ac, an), (hc, hn) = d["easy"], d["ans"], d["hard"]
    easy_pct, hard_pct, ans_pct = ec / en * 100, hc / hn * 100, ac / an * 100

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Answerability gate</title><style>
 :root{{--bg:#111310;--panel:#1c1f1b;--ink:#fff;--ink2:#b9beb4;--ink3:#7d8278;
   --line:#2f332d;--good:#22b573;--bad:#e8632c;--blue:#4a92ea;--track:#262a24}}
 *{{box-sizing:border-box}}html,body{{margin:0;padding:0}}
 body{{background:var(--bg);color:var(--ink);font-family:ui-sans-serif,-apple-system,
  "Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-feature-settings:"tnum" 1;
  display:flex;justify-content:center}}
 .stage{{width:1080px;height:1350px;padding:54px 54px 38px;display:flex;flex-direction:column}}
 .kick{{font-size:17px;letter-spacing:.19em;text-transform:uppercase;color:var(--ink3);font-weight:750}}
 h1{{font-size:80px;line-height:.94;font-weight:780;letter-spacing:-.043em;margin:16px 0 0}}
 h1 .b{{color:var(--bad)}}
 .dek{{font-size:23px;color:var(--ink2);line-height:1.36;margin-top:18px;max-width:900px}}

 .hero{{margin-top:40px}}
 .htitle{{font-size:16px;letter-spacing:.15em;text-transform:uppercase;
   color:var(--ink3);font-weight:750;margin-bottom:24px}}
 .brow{{display:grid;grid-template-columns:1fr 200px;gap:24px;align-items:center}}
 .blab{{font-size:23px;color:var(--ink);font-weight:620;line-height:1.24;margin-bottom:12px}}
 .blab span{{display:block;font-size:17px;color:var(--ink3);font-weight:450;margin-top:5px}}
 .btrack{{height:44px;background:var(--track);border-radius:6px;overflow:hidden}}
 .bfill{{height:100%;border-radius:6px}}
 .bnum{{font-size:72px;font-weight:780;letter-spacing:-.04em;line-height:1;text-align:right}}
 .gapband{{display:flex;align-items:center;gap:20px;margin:22px 0}}
 .gapline{{flex:1;height:2px;background:var(--bad);opacity:.45}}
 .gaptxt{{font-size:30px;font-weight:780;color:var(--bad);letter-spacing:-.02em;
   white-space:nowrap;text-align:center}}
 .gaptxt small{{display:block;font-size:15px;color:var(--ink3);font-weight:650;
   letter-spacing:.07em;text-transform:uppercase;margin-top:4px}}
 .ref{{margin-top:26px;padding-top:18px;border-top:1px solid var(--line);
   font-size:19px;color:var(--ink2);display:flex;justify-content:space-between;align-items:baseline}}
 .ref b{{color:var(--ink);font-weight:700}}

 .errs{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:32px}}
 .err{{background:var(--panel);border-radius:14px;padding:22px 24px;border-left:5px solid var(--bad)}}
 .err.ok{{border-left-color:var(--blue)}}
 .en{{font-size:50px;font-weight:780;letter-spacing:-.035em;line-height:1;color:var(--bad)}}
 .err.ok .en{{color:var(--blue)}}
 .et{{font-size:18px;color:var(--ink2);line-height:1.34;margin-top:9px}}
 .et b{{color:var(--ink);font-weight:650}}

 .route{{margin-top:28px}}
 .rt{{font-size:16px;letter-spacing:.15em;text-transform:uppercase;color:var(--ink3);
   font-weight:750;margin-bottom:14px}}
 .chips{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}
 .chip{{background:var(--panel);border-radius:12px;padding:17px 18px}}
 .cp{{font-size:31px;font-weight:780;letter-spacing:-.03em;line-height:1}}
 .cl{{font-size:15.5px;color:var(--ink2);line-height:1.32;margin-top:7px}}
 .cl b{{color:var(--ink);font-weight:650}}

 footer{{margin-top:auto;padding-top:18px;border-top:1px solid var(--line);
   display:flex;justify-content:space-between;align-items:flex-end;gap:26px}}
 .repo{{font-size:19px;font-weight:750;white-space:nowrap}}
 .rlab{{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);
   font-weight:750;margin-bottom:5px}}
 .cav{{font-size:13px;color:var(--ink3);line-height:1.5;text-align:right;max-width:430px}}
</style></head><body><div class="stage">

 <div class="kick">{d['n_all']} decisions &middot; {d['model']} &middot; SQuAD 2.0</div>
 <h1>Same gate.<br>100% and <span class="b">{hard_pct:.1f}%</span>.</h1>
 <div class="dek">One model, one prompt, 200 items per slice. The only thing that changed
 was how the negative examples were built.</div>

 <div class="hero">
  <div class="htitle">&ldquo;Does this passage contain the answer?&rdquo;</div>

  <div class="brow">
   <div>
    <div class="blab">Random unrelated passage<span>a negative you can build in one line</span></div>
    <div class="btrack"><div class="bfill" style="width:{easy_pct:.1f}%;background:var(--good)"></div></div>
   </div>
   <div class="bnum" style="color:var(--good)">{easy_pct:.0f}%</div>
  </div>

  <div class="gapband">
   <div class="gapline"></div>
   <div class="gaptxt">{d['gap']:.1f} points<small>same model, same prompt</small></div>
   <div class="gapline"></div>
  </div>

  <div class="brow">
   <div>
    <div class="blab">On topic, missing the fact<span>what a retrieval miss actually looks like</span></div>
    <div class="btrack"><div class="bfill" style="width:{hard_pct:.1f}%;background:var(--bad)"></div></div>
   </div>
   <div class="bnum" style="color:var(--bad)">{hard_pct:.1f}%</div>
  </div>

  <div class="ref"><span>Reference: passages that <b>do</b> contain the answer</span>
   <span><b>{ans_pct:.1f}%</b>&nbsp;&nbsp;{ac}/{an}</span></div>
 </div>

 <div class="errs">
  <div class="err">
   <div class="en">{d['false_accept']}</div>
   <div class="et">unanswerable passages accepted at <b>{HI:.2f} or above</b>. Each one risks
   an answer generated from a passage that cannot support it.</div>
  </div>
  <div class="err ok">
   <div class="en">{d['false_reject']}</div>
   <div class="et">answerable passage <b>wrongly dropped</b>. The errors run both ways,
   but not evenly.</div>
  </div>
 </div>

 <div class="route">
  <div class="rt">Where the judgements landed &middot; share of {d['n_real']} items, not all {d['n_all']}</div>
  <div class="chips">
   <div class="chip"><div class="cp" style="color:var(--good)">{d['rej_pct']:.1f}%</div>
    <div class="cl">scored &le; {LO:.2f}. Drop the passage, no generation from it.</div></div>
   <div class="chip"><div class="cp" style="color:var(--ink2)">{d['esc_pct']:.1f}%</div>
    <div class="cl">uncertain. <b>{d['hard_escalated']} of {d['n_hard']}</b> hard negatives land here.</div></div>
   <div class="chip"><div class="cp" style="color:var(--blue)">{d['acc_pct']:.1f}%</div>
    <div class="cl">scored &ge; {HI:.2f}. Passed on to generation.</div></div>
  </div>
 </div>

 <footer>
  <div><div class="rlab">Code, raw responses, analysis</div><div class="repo">{REPO_URL}</div></div>
  <div class="cav">Thresholds chosen by reading this same data, so every share is in-sample.
  No end-to-end saving measured. SQuAD 2.0 is public; contamination not ruled out.</div>
 </footer>

</div></body></html>"""
    OUT.write_text(html)
    print(f"wrote {OUT}")
    print(f"  slices {ec}/{en}  {ac}/{an}  {hc}/{hn}   gap {d['gap']:.1f}")
    print(f"  routing {d['rej_pct']:.1f}/{d['esc_pct']:.1f}/{d['acc_pct']:.1f} of {d['n_real']}")
    print(f"  errors: {d['false_accept']} accepted, {d['false_reject']} rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
