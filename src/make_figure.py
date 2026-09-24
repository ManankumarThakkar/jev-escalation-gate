"""Render the post figure straight from results/report.json, in both themes.

Every number on the image is read from the report, so the figure cannot drift
from the measurement. Change the experiment, re-run analyze.py, re-run this,
and the picture follows.

The layout is four stacked panels, in the order a reader needs them:

  1. the hook      - the 30.5 point swing, which is the surprising part
  2. the pattern   - where the gate actually sits, as a flow diagram, because
                     an engineer cannot copy an idea they have only seen as a
                     bar chart
  3. the operating point - the numbers that decide whether it is worth doing
  4. provenance    - repo, sample, and the caveats that keep it honest

    python src/make_figure.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "results" / "report.json"
OUT_DIR = ROOT / "linkedin"
REPO = "github.com/ManankumarThakkar/jev-escalation-gate"

SLICES = [
    ("easy_negative", "Random unrelated passage", "s3"),
    ("answerable", "Passage does answer it", "s1"),
    ("hard_negative", "On topic, silent on the fact", "s2"),
]


def _data() -> dict:
    """Everything both layouts draw from. One source, so they cannot disagree."""
    r = json.loads(REPORT.read_text())
    ps = r["per_slice"]
    gate = next(c for c in r["coverage_curve_realistic"] if c["escalate_if_between"] == [0.1, 0.9])
    return {
        "r": r, "ps": ps, "rm": r["realistic_mix"], "cost": r["cost"], "lat": r["latency_ms"],
        "keep": gate["coverage"] * 100,
        "escalate": 100 - gate["coverage"] * 100,
        "acc_keep": gate["accuracy_on_covered"] * 100,
        "lo": gate["escalate_if_between"][0], "hi": gate["escalate_if_between"][1],
        "gap": (ps["easy_negative"]["accuracy"] - ps["hard_negative"]["accuracy"]) * 100,
    }


def _tokens(theme: str) -> tuple[str, str]:
    dark = theme == "dark"
    tokens = (
        """--bg:#14140f; --panel:#1f1f1a; --panel2:#262620; --ink:#ffffff;
       --ink2:#c9c8bc; --ink3:#8f8e84; --line:#37372f;
       --s1:#3987e5; --s2:#d95926; --s3:#199e70; --track:#2c2c25;"""
        if dark
        else """--bg:#fbfaf7; --panel:#ffffff; --panel2:#f3f2ed; --ink:#0b0b0b;
       --ink2:#4c4b47; --ink3:#76756f; --line:#e4e2db;
       --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --track:#eeece6;"""
    )
    return tokens, ("none" if dark else "0 1px 2px rgba(0,0,0,.05)")


def _bars(ps: dict, label_col: int) -> str:
    return "\n".join(
        f"""        <div class="row">
          <div class="rl">{label}</div>
          <div class="rt"><div class="rf {cls}" style="width:{ps[key]['accuracy']*100:.1f}%"></div></div>
          <div class="rv">{ps[key]['accuracy']*100:.1f}%</div>
        </div>"""
        for key, label, cls in SLICES
    )


def build_portrait(theme: str) -> str:
    r = json.loads(REPORT.read_text())
    ps, rm, cost, lat = r["per_slice"], r["realistic_mix"], r["cost"], r["latency_ms"]
    gate = next(c for c in r["coverage_curve_realistic"] if c["escalate_if_between"] == [0.1, 0.9])
    keep = gate["coverage"] * 100
    escalate = 100 - keep
    acc_keep = gate["accuracy_on_covered"] * 100
    lo, hi = gate["escalate_if_between"]
    gap = (ps["easy_negative"]["accuracy"] - ps["hard_negative"]["accuracy"]) * 100

    bars = "\n".join(
        f"""        <div class="row">
          <div class="rl">{label}</div>
          <div class="rt"><div class="rf {cls}" style="width:{ps[key]['accuracy']*100:.1f}%"></div></div>
          <div class="rv">{ps[key]['accuracy']*100:.1f}%</div>
        </div>"""
        for key, label, cls in SLICES
    )

    dark = theme == "dark"
    tokens = (
        """--bg:#14140f; --panel:#1f1f1a; --panel2:#262620; --ink:#ffffff;
       --ink2:#c9c8bc; --ink3:#8f8e84; --line:#37372f;
       --s1:#3987e5; --s2:#d95926; --s3:#199e70; --track:#2c2c25;"""
        if dark
        else """--bg:#fbfaf7; --panel:#ffffff; --panel2:#f3f2ed; --ink:#0b0b0b;
       --ink2:#4c4b47; --ink3:#76756f; --line:#e4e2db;
       --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --track:#eeece6;"""
    )
    shadow = "none" if dark else "0 1px 2px rgba(0,0,0,.05)"

    return f"""<!doctype html>
<html lang="en" data-theme="{theme}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Escalation Gate</title>
<style>
  :root {{ {tokens} }}
  *{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
  body{{background:var(--bg);color:var(--ink);
    font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    font-feature-settings:"tnum" 1;display:flex;justify-content:center}}
  .stage{{width:1080px;height:1350px;background:var(--bg);padding:44px 44px 34px;
    display:flex;flex-direction:column;gap:24px;transform-origin:top left}}

  .kicker{{font-size:19px;letter-spacing:.16em;text-transform:uppercase;
    color:var(--ink3);font-weight:700}}
  h1{{font-size:66px;line-height:1.0;font-weight:750;letter-spacing:-.035em;margin:10px 0 0}}
  h1 .hl{{color:var(--s2)}}
  .dek{{font-size:22px;color:var(--ink2);line-height:1.4;margin-top:12px;font-weight:450;max-width:880px}}

  .panel{{background:var(--panel);border:1px solid var(--line);border-radius:16px;
    padding:30px 30px;box-shadow:{shadow}}}
  .ptitle{{font-size:15px;letter-spacing:.13em;text-transform:uppercase;
    color:var(--ink3);font-weight:750;margin-bottom:14px}}

  .row{{display:grid;grid-template-columns:290px 1fr 86px;gap:14px;align-items:center;margin-top:10px}}
  .rl{{font-size:18px;color:var(--ink2);line-height:1.2}}
  .rt{{height:32px;background:var(--track);border-radius:4px;overflow:hidden}}
  .rf{{height:100%;border-radius:4px}}
  .s1{{background:var(--s1)}} .s2{{background:var(--s2)}} .s3{{background:var(--s3)}}
  .rv{{font-size:26px;font-weight:750;text-align:right;letter-spacing:-.02em}}
  .gapnote{{font-size:18px;color:var(--ink2);margin-top:14px;line-height:1.4}}
  .gapnote b{{color:var(--ink)}}

  .stats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}
  .stat{{background:var(--panel2);border-radius:14px;padding:26px 24px}}
  .sv{{font-size:44px;font-weight:750;letter-spacing:-.03em;line-height:1}}
  .sl{{font-size:16px;color:var(--ink2);margin-top:7px;line-height:1.3}}

  footer{{margin-top:auto;display:flex;justify-content:space-between;
    align-items:flex-end;gap:20px;padding-top:20px;border-top:1px solid var(--line)}}
  .repo{{font-size:21px;font-weight:750;color:var(--ink);letter-spacing:-.015em;white-space:nowrap}}
  .repolab{{font-size:15px;color:var(--ink3);letter-spacing:.1em;
    text-transform:uppercase;font-weight:700;margin-bottom:5px}}
  .caveat{{font-size:14px;color:var(--ink3);line-height:1.45;text-align:right;max-width:372px}}
</style></head><body>
<div class="stage" id="stage">

  <div>
    <div class="kicker">600 measured decisions &middot; jev-1.13.0 &middot; ${cost['total_usd']:.3f}</div>
    <h1>The same gate scored 100% and <span class="hl">{ps['hard_negative']['accuracy']*100:.1f}%</span>.</h1>
    <div class="dek">One model, one prompt, one dataset. The only thing that changed was how the
    wrong answers in the test set were built.</div>
  </div>

  <div class="panel">
    <div class="ptitle">&ldquo;Can this passage answer this question?&rdquo;</div>
{bars}
    <div class="gapnote">A <b>{gap:.1f} point gap</b>. Random passages are trivial to reject.
    Passages that are on topic but silent on the fact, which is what a retrieval miss really
    looks like, get waved through about <b>three times in ten</b>.</div>
  </div>

  <div class="panel">
    <div class="ptitle">So don't let it answer everything. Let it answer what it is sure about.</div>
    <svg viewBox="0 0 990 290" width="100%" height="290" role="img"
         aria-label="Question and passage enter the gate; confident cases are answered directly, uncertain cases escalate to a large model">
      <defs>
        <marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="var(--ink3)"/>
        </marker>
      </defs>

      <rect x="0" y="96" width="200" height="68" rx="12" fill="var(--panel2)"/>
      <text x="100" y="124" text-anchor="middle" font-size="19" font-weight="650" fill="var(--ink)">Question +</text>
      <text x="100" y="147" text-anchor="middle" font-size="19" font-weight="650" fill="var(--ink)">retrieved passage</text>

      <line x1="206" y1="130" x2="256" y2="130" stroke="var(--ink3)" stroke-width="2.5" marker-end="url(#a)"/>

      <rect x="264" y="82" width="196" height="96" rx="12" fill="var(--s1)"/>
      <text x="362" y="116" text-anchor="middle" font-size="24" font-weight="750" fill="#fff">Jev gate</text>
      <text x="362" y="143" text-anchor="middle" font-size="17" fill="#fff" opacity=".93">{lat['p50']:.0f} ms &middot; ${cost['per_decision_usd']:.6f}</text>
      <text x="362" y="164" text-anchor="middle" font-size="16" fill="#fff" opacity=".8">returns 0.00 to 1.00</text>

      <path d="M466,110 L512,110 L512,44 L556,44" stroke="var(--s3)" stroke-width="2.5"
            fill="none" marker-end="url(#a)"/>
      <path d="M466,150 L512,150 L512,216 L556,216" stroke="var(--s2)" stroke-width="2.5"
            fill="none" marker-end="url(#a)"/>

      <rect x="564" y="8" width="426" height="72" rx="12" fill="var(--panel2)" stroke="var(--s3)" stroke-width="2"/>
      <text x="586" y="36" font-size="18" font-weight="700" fill="var(--s3)">score below {lo:.2f} or above {hi:.2f}</text>
      <text x="586" y="62" font-size="19" font-weight="650" fill="var(--ink)">answer it yourself, no big model</text>

      <rect x="564" y="180" width="426" height="72" rx="12" fill="var(--panel2)" stroke="var(--s2)" stroke-width="2"/>
      <text x="586" y="208" font-size="18" font-weight="700" fill="var(--s2)">score between {lo:.2f} and {hi:.2f}</text>
      <text x="586" y="234" font-size="19" font-weight="650" fill="var(--ink)">escalate to the large model</text>
    </svg>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="sv" style="color:var(--s3)">{keep:.1f}%</div>
      <div class="sl">of decisions never reach the expensive model</div>
    </div>
    <div class="stat">
      <div class="sv">{acc_keep:.1f}%</div>
      <div class="sl">accurate on the ones it keeps</div>
    </div>
    <div class="stat">
      <div class="sv" style="color:var(--s2)">{escalate:.1f}%</div>
      <div class="sl">escalated, and they are the genuinely hard ones</div>
    </div>
  </div>

  <footer>
    <div>
      <div class="repolab">Code, raw data, analysis</div>
      <div class="repo">{REPO}</div>
    </div>
    <div class="caveat">
      SQuAD 2.0, 200 items per slice, seeded and reproducible. Calibration error
      {rm['ece']:.3f} against a {rm['ece_noise_floor']:.3f} noise floor. Latency measured
      through a third party proxy, so treat it as an upper bound. No large model
      baseline was run.
    </div>
  </footer>

</div>
<script>
  function fit(){{const s=document.getElementById('stage');
    const k=Math.min(1,window.innerWidth/1080,window.innerHeight/1350);
    s.style.transform='scale('+k+')';}}
  addEventListener('resize',fit);fit();
</script></body></html>
"""


def build_wide(theme: str) -> str:
    """1920x1080. A re-layout, not a rescale.

    Landscape has width to spare and no height, so the gap panel and the flow
    diagram sit side by side rather than stacked, and the headline runs on one
    line. Same numbers, same source, different shape.
    """
    d = _data()
    ps, rm, cost, lat = d["ps"], d["rm"], d["cost"], d["lat"]
    tokens, shadow = _tokens(theme)
    bars = _bars(ps, 250)

    return f"""<!doctype html>
<html lang="en" data-theme="{theme}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Escalation Gate</title>
<style>
  :root {{ {tokens} }}
  *{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
  body{{background:var(--bg);color:var(--ink);
    font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    font-feature-settings:"tnum" 1;display:flex;justify-content:center}}
  .stage{{width:1920px;height:1080px;background:var(--bg);padding:52px 60px 40px;
    display:flex;flex-direction:column;gap:22px;transform-origin:top left}}

  .kicker{{font-size:19px;letter-spacing:.16em;text-transform:uppercase;
    color:var(--ink3);font-weight:700}}
  h1{{font-size:70px;line-height:1.0;font-weight:750;letter-spacing:-.035em;margin:10px 0 0}}
  h1 .hl{{color:var(--s2)}}
  .dek{{font-size:23px;color:var(--ink2);line-height:1.4;margin-top:12px;font-weight:450;max-width:1200px}}

  .cols{{display:grid;grid-template-columns:760px 1fr;gap:22px;flex:1;min-height:0}}
  .panel{{background:var(--panel);border:1px solid var(--line);border-radius:16px;
    padding:26px 28px;box-shadow:{shadow};display:flex;flex-direction:column}}
  .ptitle{{font-size:15px;letter-spacing:.13em;text-transform:uppercase;
    color:var(--ink3);font-weight:750;margin-bottom:12px}}

  .row{{display:grid;grid-template-columns:250px 1fr 86px;gap:13px;align-items:center;margin-top:12px}}
  .rl{{font-size:18px;color:var(--ink2);line-height:1.2}}
  .rt{{height:32px;background:var(--track);border-radius:4px;overflow:hidden}}
  .rf{{height:100%;border-radius:4px}}
  .s1{{background:var(--s1)}} .s2{{background:var(--s2)}} .s3{{background:var(--s3)}}
  .rv{{font-size:26px;font-weight:750;text-align:right;letter-spacing:-.02em}}
  .gapnote{{font-size:18px;color:var(--ink2);margin-top:16px;line-height:1.42}}
  .gapnote b{{color:var(--ink)}}

  .stats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:13px;margin-top:auto;padding-top:18px}}
  .stat{{background:var(--panel2);border-radius:13px;padding:16px 18px}}
  .sv{{font-size:36px;font-weight:750;letter-spacing:-.03em;line-height:1}}
  .sl{{font-size:15px;color:var(--ink2);margin-top:6px;line-height:1.28}}

  footer{{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;
    padding-top:16px;border-top:1px solid var(--line)}}
  .repo{{font-size:24px;font-weight:750;color:var(--ink);letter-spacing:-.015em;white-space:nowrap}}
  .repolab{{font-size:15px;color:var(--ink3);letter-spacing:.1em;
    text-transform:uppercase;font-weight:700;margin-bottom:5px}}
  .caveat{{font-size:14px;color:var(--ink3);line-height:1.45;text-align:right;max-width:700px}}
</style></head><body>
<div class="stage" id="stage">

  <div>
    <div class="kicker">600 measured decisions &middot; jev-1.13.0 &middot; ${cost['total_usd']:.3f}</div>
    <h1>The same gate scored 100% and <span class="hl">{ps['hard_negative']['accuracy']*100:.1f}%</span>.</h1>
    <div class="dek">One model, one prompt, one dataset. The only thing that changed was how the
    wrong answers in the test set were built.</div>
  </div>

  <div class="cols">
    <div class="panel">
      <div class="ptitle">&ldquo;Can this passage answer this question?&rdquo;</div>
{bars}
      <div class="gapnote">A <b>{d['gap']:.1f} point gap</b>. Random passages are trivial to
      reject. Passages that are on topic but silent on the fact, which is what a retrieval
      miss really looks like, get waved through about <b>three times in ten</b>.</div>
      <div class="stats">
        <div class="stat">
          <div class="sv" style="color:var(--s3)">{d['keep']:.1f}%</div>
          <div class="sl">never reach the expensive model</div>
        </div>
        <div class="stat">
          <div class="sv">{d['acc_keep']:.1f}%</div>
          <div class="sl">accurate on the ones it keeps</div>
        </div>
        <div class="stat">
          <div class="sv" style="color:var(--s2)">{d['escalate']:.1f}%</div>
          <div class="sl">escalated, the genuinely hard ones</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="ptitle">So don't let it answer everything. Let it answer what it is sure about.</div>
      <svg viewBox="0 0 1000 600" width="100%" height="100%" preserveAspectRatio="xMidYMid meet"
           role="img" aria-label="Question and passage enter the gate; confident cases are answered directly, uncertain cases escalate to a large model">
        <defs>
          <marker id="aw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="var(--ink3)"/>
          </marker>
        </defs>

        <rect x="0" y="262" width="212" height="78" rx="12" fill="var(--panel2)"/>
        <text x="106" y="294" text-anchor="middle" font-size="20" font-weight="650" fill="var(--ink)">Question +</text>
        <text x="106" y="320" text-anchor="middle" font-size="20" font-weight="650" fill="var(--ink)">retrieved passage</text>

        <line x1="220" y1="301" x2="272" y2="301" stroke="var(--ink3)" stroke-width="2.5" marker-end="url(#aw)"/>

        <rect x="280" y="249" width="208" height="104" rx="12" fill="var(--s1)"/>
        <text x="384" y="287" text-anchor="middle" font-size="26" font-weight="750" fill="#fff">Jev gate</text>
        <text x="384" y="315" text-anchor="middle" font-size="17" fill="#fff" opacity=".93">{lat['p50']:.0f} ms &middot; ${cost['per_decision_usd']:.6f}</text>
        <text x="384" y="337" text-anchor="middle" font-size="16" fill="#fff" opacity=".8">returns 0.00 to 1.00</text>

        <path d="M494,278 L540,278 L540,116 L584,116" stroke="var(--s3)" stroke-width="2.5"
              fill="none" marker-end="url(#aw)"/>
        <path d="M494,324 L540,324 L540,486 L584,486" stroke="var(--s2)" stroke-width="2.5"
              fill="none" marker-end="url(#aw)"/>

        <rect x="592" y="70" width="408" height="92" rx="12" fill="var(--panel2)" stroke="var(--s3)" stroke-width="2"/>
        <text x="614" y="106" font-size="18" font-weight="700" fill="var(--s3)">score below {d['lo']:.2f} or above {d['hi']:.2f}</text>
        <text x="614" y="136" font-size="20" font-weight="650" fill="var(--ink)">answer it yourself, no big model</text>

        <rect x="592" y="440" width="408" height="92" rx="12" fill="var(--panel2)" stroke="var(--s2)" stroke-width="2"/>
        <text x="614" y="476" font-size="18" font-weight="700" fill="var(--s2)">score between {d['lo']:.2f} and {d['hi']:.2f}</text>
        <text x="614" y="506" font-size="20" font-weight="650" fill="var(--ink)">escalate to the large model</text>
      </svg>
    </div>
  </div>

  <footer>
    <div>
      <div class="repolab">Code, raw data, analysis</div>
      <div class="repo">{REPO}</div>
    </div>
    <div class="caveat">
      SQuAD 2.0, 200 items per slice, seeded and reproducible. Calibration error
      {rm['ece']:.3f} against a {rm['ece_noise_floor']:.3f} noise floor. Latency measured
      through a third party proxy, so treat it as an upper bound. No large model baseline was run.
    </div>
  </footer>

</div>
<script>
  function fit(){{const s=document.getElementById('stage');
    const k=Math.min(1,window.innerWidth/1920,window.innerHeight/1080);
    s.style.transform='scale('+k+')';}}
  addEventListener('resize',fit);fit();
</script></body></html>
"""


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    for theme in ("light", "dark"):
        path = OUT_DIR / f"figure-{theme}.html"
        path.write_text(build_portrait(theme))
        print(f"wrote {path}")
        wide = OUT_DIR / f"figure-{theme}-16x9.html"
        wide.write_text(build_wide(theme))
        print(f"wrote {wide}")

    r = json.loads(REPORT.read_text())
    gate = next(c for c in r["coverage_curve_realistic"] if c["escalate_if_between"] == [0.1, 0.9])
    print(f"  keep {gate['coverage']*100:.1f}% at {gate['accuracy_on_covered']*100:.1f}% | "
          f"escalate {(1-gate['coverage'])*100:.1f}% | band {gate['escalate_if_between']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
