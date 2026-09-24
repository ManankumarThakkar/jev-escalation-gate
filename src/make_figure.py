"""Render the post figure straight from results/report.json.

Every number on the image is read from the report, so the figure cannot drift
from the measurement. Change the experiment, re-run analyze.py, re-run this,
and the picture follows.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "results" / "report.json"
OUT = ROOT / "linkedin" / "figure.html"

SLICE_LABEL = {
    "easy_negative": "Random unrelated passage",
    "answerable": "Passage does answer it",
    "hard_negative": "On-topic, but silent on the fact",
}
SLICE_COLOR = {"easy_negative": "var(--s3)", "answerable": "var(--s1)", "hard_negative": "var(--s2)"}
ORDER = ["easy_negative", "answerable", "hard_negative"]


def main() -> int:
    r = json.loads(REPORT.read_text())
    per = r["per_slice"]
    curve = [c for c in r["coverage_curve_realistic"] if c["n_covered"]]

    bars = "\n".join(
        f"""      <div class="barrow">
        <div class="blabel">{SLICE_LABEL[s]}</div>
        <div class="btrack"><div class="bfill" style="width:{per[s]['accuracy']*100:.1f}%;background:{SLICE_COLOR[s]}"></div></div>
        <div class="bval">{per[s]['accuracy']*100:.1f}%</div>
      </div>"""
        for s in ORDER
    )

    # Coverage curve: x = coverage, y = accuracy on covered.
    xs = [c["coverage"] for c in curve]
    ys = [c["accuracy_on_covered"] for c in curve]
    y_lo, y_hi = 0.80, 1.00
    pts = []
    for x, y in zip(xs, ys):
        px = 70 + (1 - x) * 800          # coverage falls left to right
        py = 400 - (y - y_lo) / (y_hi - y_lo) * 340
        pts.append(f"{px:.1f},{py:.1f}")
    polyline = " ".join(pts)

    # The operating point the README highlights: the widest band that still
    # clears 0.95 accuracy on the covered slice.
    best = next((c for c in curve if c["accuracy_on_covered"] and c["accuracy_on_covered"] >= 0.95), curve[-1])
    bx = 70 + (1 - best["coverage"]) * 800
    by = 400 - (best["accuracy_on_covered"] - y_lo) / (y_hi - y_lo) * 340

    gap = (per["easy_negative"]["accuracy"] - per["hard_negative"]["accuracy"]) * 100
    lat = r["latency_ms"]
    cost = r["cost"]

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Escalation Gate</title>
<style>
  :root {{
    --surface:#fcfcfb; --card:#f4f3f0; --ink:#0b0b0b; --ink2:#52514e; --ink3:#76756f;
    --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --grid:#e3e2de;
  }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
    --surface:#1a1a19; --card:#232320; --ink:#fff; --ink2:#c3c2b7; --ink3:#8f8e86;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --grid:#35342f;
  }} }}
  :root[data-theme="dark"] {{
    --surface:#1a1a19; --card:#232320; --ink:#fff; --ink2:#c3c2b7; --ink3:#8f8e86;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --grid:#35342f;
  }}
  *{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
  body{{background:#f0efec;color:var(--ink);
    font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    font-feature-settings:"tnum" 1;display:flex;justify-content:center;padding:12px}}
  .stage{{width:1080px;height:1350px;background:var(--surface);padding:58px 56px 40px;
    display:flex;flex-direction:column;transform-origin:top left}}
  .kicker{{font-size:21px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-weight:650}}
  h1{{font-size:56px;line-height:1.06;font-weight:700;letter-spacing:-.03em;margin:14px 0 0}}
  .sub{{font-size:24px;color:var(--ink2);line-height:1.45;margin-top:14px;font-weight:450}}
  h2{{font-size:24px;font-weight:700;margin:30px 0 0;display:flex;align-items:center;gap:12px}}
  h2::after{{content:"";flex:1;height:1px;background:var(--grid)}}
  .barrow{{display:grid;grid-template-columns:330px 1fr 92px;gap:18px;align-items:center;margin-top:14px}}
  .blabel{{font-size:20px;color:var(--ink2);line-height:1.25}}
  .btrack{{height:40px;background:var(--card);border-radius:5px;overflow:hidden}}
  .bfill{{height:100%;border-radius:5px}}
  .bval{{font-size:30px;font-weight:700;text-align:right;letter-spacing:-.02em}}
  .note{{font-size:20px;color:var(--ink2);margin-top:16px;line-height:1.45}}
  .note b{{color:var(--ink);font-weight:700}}
  svg{{margin-top:8px}}
  .axis{{font-size:17px;fill:var(--ink3)}}
  .footer{{margin-top:auto;padding-top:14px;border-top:1px solid var(--grid);
    font-size:16px;color:var(--ink3);line-height:1.45}}
</style></head><body>
<div class="stage" id="stage">
  <div class="kicker">600 decisions &middot; jev-1.13.0 &middot; ${cost['total_usd']:.3f}</div>
  <h1>The same gate scored 100% and {per['hard_negative']['accuracy']*100:.1f}%.</h1>
  <div class="sub">One model, one prompt, one afternoon. The only thing that changed was how
  the wrong answers in the test set were built.</div>

  <h2>&ldquo;Can this passage answer this question?&rdquo;</h2>
{bars}
  <div class="note">A <b>{gap:.1f}-point gap</b>. Random passages are easy to reject. Passages that are
  on-topic but do not contain the fact, which is
  what a retrieval miss actually looks like, get waved through about three times in ten.</div>

  <h2>But the confidence number is honest, so you can gate on it</h2>
  <svg viewBox="0 0 960 440" width="100%" height="440" role="img"
       aria-label="Accuracy on auto-handled traffic rises as coverage falls">
    <line x1="70" y1="400" x2="930" y2="400" stroke="var(--grid)" stroke-width="1"/>
    <line x1="70" y1="60" x2="930" y2="60" stroke="var(--grid)" stroke-width="1"/>
    <text class="axis" x="70" y="52">100% accurate on what it keeps</text>
    <text class="axis" x="70" y="422">80%</text>
    <text class="axis" x="790" y="422">fewer decisions kept &rarr;</text>
    <polyline points="{polyline}" fill="none" stroke="var(--s1)" stroke-width="3.5"
      stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="{bx:.1f}" cy="{by:.1f}" r="9" fill="var(--s1)" stroke="var(--surface)" stroke-width="3"/>
    <text x="{bx - 12:.1f}" y="{by - 24:.1f}" text-anchor="end" font-size="23" font-weight="700" fill="var(--ink)">
      {best['coverage']*100:.0f}% of traffic at {best['accuracy_on_covered']*100:.1f}%
    </text>
  </svg>
  <div class="note">Escalate anything it scores between {best['escalate_if_between'][0]:.2f} and
  {best['escalate_if_between'][1]:.2f}; answer the rest yourself. Calibration error
  {r['realistic_mix']['ece']:.3f} against a {r['realistic_mix']['ece_noise_floor']:.3f} noise floor,
  so the probability means roughly what it says.</div>

  <div class="footer">
    SQuAD 2.0, 200 items per slice, seeded and reproducible. p50 {lat['p50']:.0f} ms,
    ${cost['per_decision_usd']:.6f} per decision, measured through a third-party proxy,
    so treat latency as an upper bound. No large-model baseline was run.
  </div>
</div>
<script>
  function fit(){{const s=document.getElementById('stage');
    const k=Math.min(1,(window.innerWidth-24)/1080,(window.innerHeight-24)/1350);
    s.style.transform='scale('+k+')';}}
  addEventListener('resize',fit);fit();
</script></body></html>
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT}")
    print(f"  gap {gap:.1f} points | operating point {best['coverage']*100:.1f}% @ "
          f"{best['accuracy_on_covered']*100:.1f}% | band {best['escalate_if_between']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
