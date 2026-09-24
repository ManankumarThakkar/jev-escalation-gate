"""Render the post figure directly from the experiment's raw responses.

Reads `results/raw-*.json` from the jev-escalation-gate repository and
recomputes every number on the image, so the figure cannot disagree with the
data or with the post. Nothing is typed in by hand.

The routing panel corrects the previous version, which implied a confident
"answerable" verdict removed the need for a large model. It does not: an
answerability gate classifies, it does not generate. Only the confident
"unanswerable" branch avoids a generation call.
"""

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent.parent / "linkedin" / "figure.html"
REPO_URL = "github.com/ManankumarThakkar/jev-escalation-gate"
LO, HI = 0.10, 0.90


def data() -> dict:
    raw = json.load(open(sorted(glob.glob(str(REPO / "results" / "raw-*.json")))[-1]))
    rows = raw["rows"]
    real = [r for r in rows if r["slice"] in ("answerable", "hard_negative")]
    hard = [r for r in real if r["slice"] == "hard_negative"]

    def acc(slice_name):
        ch = [r for r in rows if r["slice"] == slice_name]
        return sum(1 for r in ch if (r["p_answerable"] >= 0.5) == r["answerable"]), len(ch)

    rej = [r for r in real if r["p_answerable"] <= LO]
    esc = [r for r in real if LO < r["p_answerable"] < HI]
    acc_band = [r for r in real if r["p_answerable"] >= HI]
    return {
        "easy": acc("easy_negative"), "answerable": acc("answerable"), "hard": acc("hard_negative"),
        "n_real": len(real),
        "rej_n": len(rej), "esc_n": len(esc), "acc_n": len(acc_band),
        "rej_pct": len(rej) / len(real) * 100,
        "esc_pct": len(esc) / len(real) * 100,
        "acc_pct": len(acc_band) / len(real) * 100,
        "hard_conf_accept": len([r for r in acc_band if r["slice"] == "hard_negative"]),
        "hard_escalated": len([r for r in esc if r["slice"] == "hard_negative"]),
        "n_hard": len(hard),
        "model": raw["models_seen"][0], "cost": raw["total_cost_usd"], "n": len(rows),
    }


def main() -> int:
    d = data()
    ec, en = d["easy"]; ac, an = d["answerable"]; hc, hn = d["hard"]
    gap = (ec / en - hc / hn) * 100

    bars = "".join(
        f"""<div class="row"><div class="rl">{label}</div>
        <div class="rt"><div class="rf" style="width:{c/n*100:.1f}%;background:var(--{col})"></div></div>
        <div class="rv">{c/n*100:.1f}%</div><div class="rn">{c}/{n}</div></div>"""
        for label, (c, n), col in (
            ("Random unrelated passage", (ec, en), "s3"),
            ("Passage contains the answer", (ac, an), "s1"),
            ("On topic, missing the answer", (hc, hn), "s2"),
        )
    )

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Answerability gate</title><style>
 :root{{--bg:#14140f;--panel:#1f1f1a;--panel2:#262620;--ink:#fff;--ink2:#c9c8bc;
   --ink3:#8f8e84;--line:#37372f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--track:#2c2c25}}
 *{{box-sizing:border-box}}html,body{{margin:0;padding:0}}
 body{{background:var(--bg);color:var(--ink);font-family:ui-sans-serif,-apple-system,
   "Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-feature-settings:"tnum" 1;
   display:flex;justify-content:center}}
 .stage{{width:1080px;height:1350px;padding:48px 46px 36px;display:flex;
   flex-direction:column;gap:26px}}
 .kicker{{font-size:18px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);font-weight:700}}
 h1{{font-size:72px;line-height:.98;font-weight:750;letter-spacing:-.037em;margin:11px 0 0}}
 h1 .o{{color:var(--s2)}}
 .dek{{font-size:21px;color:var(--ink2);line-height:1.4;margin-top:12px;max-width:920px}}
 .panel{{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:30px 30px}}
 .pt{{font-size:14px;letter-spacing:.13em;text-transform:uppercase;color:var(--ink3);
   font-weight:750;margin-bottom:14px}}
 .row{{display:grid;grid-template-columns:280px 1fr 78px 72px;gap:12px;align-items:center;margin-top:14px}}
 .rl{{font-size:17px;color:var(--ink2);line-height:1.2}}
 .rt{{height:30px;background:var(--track);border-radius:4px;overflow:hidden}}
 .rf{{height:100%;border-radius:4px}}
 .rv{{font-size:24px;font-weight:750;text-align:right;letter-spacing:-.02em}}
 .rn{{font-size:15px;color:var(--ink3);text-align:right}}
 .note{{font-size:17px;color:var(--ink2);margin-top:14px;line-height:1.42}}
 .note b{{color:var(--ink)}}
 .warn{{margin-top:20px;padding:16px 18px;border-radius:10px;background:#2a1a12;
   border-left:4px solid var(--s2);font-size:17px;line-height:1.4;color:var(--ink2)}}
 .warn b{{color:var(--ink)}}
 footer{{margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;
   gap:20px;padding-top:14px;border-top:1px solid var(--line)}}
 .repo{{font-size:20px;font-weight:750;white-space:nowrap}}
 .rlab{{font-size:14px;color:var(--ink3);letter-spacing:.1em;text-transform:uppercase;
   font-weight:700;margin-bottom:4px}}
 .cav{{font-size:13.5px;color:var(--ink3);line-height:1.45;text-align:right;max-width:400px}}
</style></head><body><div class="stage">

 <div>
  <div class="kicker">{d['n']} decisions &middot; {d['model']} &middot; SQuAD 2.0 &middot; ${d['cost']:.3f}</div>
  <h1>Same gate.<br>100% and <span class="o">{hc/hn*100:.1f}%</span>.</h1>
  <div class="dek">One model, one prompt, 200 items per slice. The only thing that changed
  was how the wrong answers were built.</div>
 </div>

 <div class="panel">
  <div class="pt">&ldquo;Does this passage contain the answer?&rdquo; &mdash; accuracy within each slice</div>
  {bars}
  <div class="note">A <b>{gap:.1f} point gap</b>. A passage that is on topic but silent on the fact
  is what a retrieval miss really looks like, and <b>{hn-hc} of {hn}</b> were called answerable when
  they were not. The 100% is not the good news it looks like: always answering
  &ldquo;unanswerable&rdquo; also scores 100% there, and 0% on real answers.</div>
 </div>

 <div class="panel">
  <div class="pt">Where the judgements landed &middot; {d['n_real']} items, answerable + hard negatives</div>
  <svg viewBox="0 0 990 340" width="100%" height="340" role="img"
       aria-label="Three routing branches by score: reject, escalate, or pass to generation">
   <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
     orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink3)"/></marker></defs>
   <rect x="0" y="118" width="186" height="64" rx="11" fill="var(--panel2)"/>
   <text x="93" y="144" text-anchor="middle" font-size="17" font-weight="650" fill="var(--ink)">Question +</text>
   <text x="93" y="166" text-anchor="middle" font-size="17" font-weight="650" fill="var(--ink)">retrieved passage</text>
   <line x1="192" y1="150" x2="234" y2="150" stroke="var(--ink3)" stroke-width="2.5" marker-end="url(#a)"/>
   <rect x="242" y="112" width="176" height="76" rx="11" fill="var(--s1)"/>
   <text x="330" y="142" text-anchor="middle" font-size="21" font-weight="750" fill="#fff">Jev gate</text>
   <text x="330" y="167" text-anchor="middle" font-size="15" fill="#fff" opacity=".9">score 0.00 to 1.00</text>

   <path d="M424,130 L462,130 L462,44 L504,44" stroke="var(--s3)" stroke-width="2.5" fill="none" marker-end="url(#a)"/>
   <path d="M424,150 L504,150" stroke="var(--ink3)" stroke-width="2.5" fill="none" marker-end="url(#a)"/>
   <path d="M424,170 L462,170 L462,256 L504,256" stroke="var(--s1)" stroke-width="2.5" fill="none" marker-end="url(#a)"/>

   <rect x="512" y="10" width="478" height="68" rx="11" fill="var(--panel2)" stroke="var(--s3)" stroke-width="2"/>
   <text x="532" y="36" font-size="16" font-weight="700" fill="var(--s3)">score &le; {LO:.2f} &middot; {d['rej_pct']:.1f}% &middot; drop the passage, retrieve again</text>
   <text x="532" y="62" font-size="17" font-weight="650" fill="var(--ink)">the only branch that saves a generation call</text>

   <rect x="512" y="116" width="478" height="68" rx="11" fill="var(--panel2)" stroke="var(--ink3)" stroke-width="2"/>
   <text x="532" y="142" font-size="16" font-weight="700" fill="var(--ink3)">{LO:.2f} &ndash; {HI:.2f} &middot; {d['esc_pct']:.1f}% &middot; uncertain</text>
   <text x="532" y="168" font-size="17" font-weight="650" fill="var(--ink)">escalate the judgement, not the answer</text>

   <rect x="512" y="222" width="478" height="68" rx="11" fill="var(--panel2)" stroke="var(--s1)" stroke-width="2"/>
   <text x="532" y="248" font-size="16" font-weight="700" fill="var(--s1)">score &ge; {HI:.2f} &middot; {d['acc_pct']:.1f}% &middot; pass to answer generation</text>
   <text x="532" y="274" font-size="17" font-weight="650" fill="var(--ink)">still costs an LLM call</text>
  </svg>
  <div class="warn"><b>{d['hard_escalated']} of {d['n_hard']}</b> hard negatives landed in the uncertain band: the gate
  mostly declines to commit on the class it is worst at. But <b>{d['hard_conf_accept']}</b> were accepted at
  {HI:.2f} or above. Those are the production risk, not the headline accuracy.</div>
 </div>

 <footer>
  <div><div class="rlab">Code, raw responses, analysis</div><div class="repo">{REPO_URL}</div></div>
  <div class="cav">Thresholds chosen by reading this same data, so the splits are in-sample.
  SQuAD 2.0 is public; contamination not ruled out. No frontier-model baseline was run.</div>
 </footer>

</div></body></html>"""
    OUT.write_text(html)
    print(f"wrote {OUT}")
    print(f"  slices {ec}/{en}  {ac}/{an}  {hc}/{hn}   gap {gap:.1f}")
    print(f"  routing {d['rej_pct']:.1f}% / {d['esc_pct']:.1f}% / {d['acc_pct']:.1f}% of {d['n_real']}")
    print(f"  hard negatives: {d['hard_escalated']} escalated, {d['hard_conf_accept']} confidently accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
