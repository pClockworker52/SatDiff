"""Generate a single-file HTML review homepage for the Stage 2 dataset.

Reads every <tier>_<asset>.jsonl in training/stage2_handauthored/, extracts
images + Stage A + diff + gold, embeds everything in one HTML file with
inline JS for keyboard navigation + correction tracking.

Output: /home/peter/datasets/satdiff_stage2/review.html

How to use:
    python training/build_review_page.py
    # then open file:///home/peter/datasets/satdiff_stage2/review.html in a browser

Keyboard:
    →  /  Space  : next example
    ←            : previous example
    O            : mark OK + advance
    N            : focus the note textarea
    Ctrl+S       : download corrections JSON

Corrections persist to localStorage so closing/reopening preserves state.
The "Download corrections" button writes a JSON file with one entry per
example: {pass_id: "OK"} or {pass_id: "<your correction text>"}.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
HAND = REPO_ROOT / "training" / "stage2_handauthored"
OUT = Path("/home/peter/datasets/satdiff_stage2/review.html")


def _strip_prompt_block(prompt: str, header: str, next_header: str) -> str:
    """Slice between [HEADER] and [next_header] markers in the Stage B prompt."""
    start = prompt.find(f"[{header}]")
    if start < 0:
        return ""
    end = prompt.find(f"[{next_header}]") if next_header else len(prompt)
    return prompt[start:end].strip()


# Root we serve from: HTML lives in /home/peter/datasets/satdiff_stage2/, so
# image paths must be RELATIVE to that directory for http.server to find them.
DATASET_ROOT = Path("/home/peter/datasets/satdiff_stage2")


def _to_relative(path_str: str) -> str:
    """Convert an absolute image path under the dataset root to a path
    relative to that root (so it works under http.server)."""
    p = Path(path_str)
    try:
        return str(p.relative_to(DATASET_ROOT)).replace("\\", "/")
    except ValueError:
        # Outside the served root — keep absolute (will likely 404 over HTTP
        # but at least the path is preserved for diagnosis).
        return str(p).replace("\\", "/")


def extract_example(line: str, file_tag: str, idx: int) -> dict:
    msg = json.loads(line)
    user = msg["messages"][1]["content"]
    images = [_to_relative(c["image"]) for c in user if c["type"] == "image"]
    prompt = next(c["text"] for c in user if c["type"] == "text")
    gold_str = msg["messages"][2]["content"][0]["text"]
    gold = json.loads(gold_str)

    stage_a = _strip_prompt_block(prompt, "STAGE A OBSERVATIONS", "PRIOR REPORTS")
    diff_block = _strip_prompt_block(prompt, "CURRENT PASS", "STAGE A OBSERVATIONS")
    baseline_block = _strip_prompt_block(prompt, "BASELINE", "CURRENT PASS")

    return {
        "id": f"{file_tag}_{idx}",
        "tier": file_tag.split("_")[0],
        "asset_or_subcat": "_".join(file_tag.split("_")[1:]) or "unknown",
        "pass_id": gold["pass_id"],
        "images": images,
        "stage_a": stage_a,
        "diff_block": diff_block,
        "baseline_block": baseline_block,
        "gold": gold,
    }


def main() -> int:
    examples: list[dict] = []
    for f in sorted(HAND.glob("*.jsonl")):
        file_tag = f.stem  # e.g. tier2_aswan
        for i, line in enumerate(f.read_text().splitlines()):
            if not line.strip():
                continue
            examples.append(extract_example(line, file_tag, i))

    if not examples:
        print("No examples found", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(_render_html(examples))
    print(f"Wrote {len(examples)} examples to {OUT}")
    print(f"Open in browser: file://{OUT}")
    return 0


def _render_html(examples: list[dict]) -> str:
    data_json = json.dumps(examples, indent=None)
    return HTML_TEMPLATE.replace("__DATA__", data_json).replace(
        "__N_EXAMPLES__", str(len(examples))
    )


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SatDiff Stage 2 review</title>
<style>
  body { margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#1e1e1e; color:#e0e0e0; }
  .header { padding:.5rem 1rem; border-bottom:1px solid #444; background:#2a2a2a; display:flex; justify-content:space-between; align-items:center; }
  .header h1 { margin:0; font-size:1rem; font-weight:500; color:#aaa; }
  .progress { font-family: monospace; color:#888; }
  .container { max-width: 1400px; margin: 0 auto; padding: 1rem; }
  .nav-row { display:flex; gap: .5rem; margin-bottom: 1rem; align-items:center; }
  button { background:#3b3b3b; color:#e0e0e0; border:1px solid #555; padding:.5rem 1rem; border-radius:.25rem; cursor:pointer; font-size: .9rem; }
  button:hover { background:#4b4b4b; }
  button.primary { background:#1565c0; border-color:#1565c0; }
  button.primary:hover { background:#1976d2; }
  button.danger  { background:#c62828; border-color:#c62828; }
  button.danger:hover { background:#d32f2f; }
  button:disabled { opacity:.4; cursor:not-allowed; }
  .ex-title { flex:1; font-weight:600; padding: 0 1rem; color:#fff; }
  .ex-meta { font-family: monospace; font-size: .85rem; color: #888; }
  .img-grid { display:grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin-bottom: 1rem; }
  .img-cell { background:#2a2a2a; border-radius:.25rem; padding: .5rem; }
  .img-cell .label { font-size:.75rem; color:#888; margin-bottom:.25rem; font-family: monospace; }
  .img-cell img { width:100%; height:auto; display:block; image-rendering: pixelated; }
  .panel { background:#2a2a2a; border-radius:.25rem; padding: 1rem; margin-bottom: 1rem; }
  .panel h2 { margin: 0 0 .5rem 0; font-size: .9rem; color:#aaa; text-transform:uppercase; letter-spacing: .05em; }
  .panel pre { white-space: pre-wrap; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:.85rem; color:#ddd; margin:0; }
  details { margin-top:.5rem; }
  summary { cursor:pointer; font-size:.85rem; color:#888; padding:.25rem 0; }
  summary:hover { color: #ccc; }
  .claim-row { padding: .25rem 0; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:.85rem; }
  .sev-nominal { color: #4caf50; }
  .sev-elevated { color: #ff9800; }
  .sev-urgent { color: #f44336; font-weight: bold; }
  .review-row { display:flex; gap:.5rem; align-items:flex-start; margin-top:1rem; padding:1rem; background:#2a2a2a; border-radius:.25rem; }
  .review-row textarea { flex:1; min-height: 4rem; background:#1e1e1e; color:#e0e0e0; border:1px solid #555; padding:.5rem; font-family: inherit; font-size:.9rem; border-radius:.25rem; resize: vertical; }
  .status-pill { display:inline-block; padding: .15rem .5rem; border-radius: 1rem; font-size: .75rem; font-family: monospace; margin-left: .5rem; }
  .status-ok { background:#1b5e20; color:#a5d6a7; }
  .status-correction { background:#bf360c; color:#ffccbc; }
  .status-pending { background:#444; color:#888; }
  .help { font-size:.8rem; color:#666; padding-top:.5rem; }
</style>
</head>
<body>

<div class="header">
  <h1>SatDiff Stage 2 — review (<span id="n">__N_EXAMPLES__</span> examples)</h1>
  <div class="progress" id="progress">…</div>
</div>

<div class="container">

  <div class="nav-row">
    <button id="prev" title="previous (←)">←</button>
    <div class="ex-title" id="ex-title">…</div>
    <span id="status-pill" class="status-pill status-pending">pending</span>
    <button id="next" class="primary" title="next (→ or space)">→ next</button>
  </div>

  <div class="ex-meta" id="ex-meta">…</div>

  <div class="img-grid" id="img-grid"></div>

  <div class="panel"><h2>Stage A observations</h2><pre id="stage-a">…</pre></div>

  <div class="panel"><h2>Gold severity</h2><div id="gold-claims">…</div>
    <details><summary>Full gold JSON</summary><pre id="gold-full">…</pre></details>
  </div>

  <div class="panel">
    <details><summary>[BASELINE] block</summary><pre id="baseline-block">…</pre></details>
    <details><summary>[CURRENT PASS] diff block</summary><pre id="diff-block">…</pre></details>
  </div>

  <div class="review-row">
    <button id="ok" class="primary" title="mark OK + advance (O)">✓ OK</button>
    <textarea id="note" placeholder="Optional correction note. Type to mark as 'needs correction'. Empty = OK."></textarea>
  </div>

  <div class="help">
    Keyboard: <code>← →</code> navigate · <code>space</code> next · <code>O</code> OK · <code>N</code> focus note · <code>Ctrl+S</code> download corrections.
  </div>

  <div class="nav-row" style="margin-top: 2rem;">
    <button id="export" class="primary">Download corrections JSON</button>
    <button id="reset" class="danger">Reset all (clear localStorage)</button>
    <span id="export-summary" style="margin-left:1rem; color:#888; font-size:.85rem;"></span>
  </div>

</div>

<script type="application/json" id="data">__DATA__</script>
<script>
const examples = JSON.parse(document.getElementById('data').textContent);
let cursor = 0;
const STORAGE_KEY = 'satdiff-stage2-corrections-v1';

function loadCorrections() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
  catch (_) { return {}; }
}
function saveCorrections(c) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
}
let corrections = loadCorrections();

function fileUrl(p) {
  // Image paths are now relative to the dataset root (where review.html
  // lives). The browser resolves them against the page URL — works under
  // python -m http.server. If a path slipped through as absolute, fall
  // back to a file:// URL.
  return p.startsWith('/') ? 'file://' + p : p;
}

function severityClass(sev) {
  return 'sev-' + sev;
}

function render() {
  const ex = examples[cursor];

  document.getElementById('progress').textContent =
    (cursor + 1) + ' / ' + examples.length;
  document.getElementById('ex-title').textContent =
    ex.tier.toUpperCase() + ' · ' + ex.asset_or_subcat + ' · ' + ex.pass_id;
  document.getElementById('ex-meta').textContent =
    'overall=' + ex.gold.overall_status +
    ' · downlink=' + ex.gold.downlink_priority +
    ' · escalation=' + ex.gold.regulatory_escalation_flag;

  // Images
  const labels = ['baseline RGB', 'baseline NIR', 'current RGB', 'current NIR'];
  const grid = document.getElementById('img-grid');
  grid.innerHTML = '';
  ex.images.forEach((p, i) => {
    const cell = document.createElement('div');
    cell.className = 'img-cell';
    cell.innerHTML =
      '<div class="label">' + labels[i] + '<br>' +
      p.split('/').pop() + '</div>' +
      '<img loading="eager" src="' + fileUrl(p) + '">';
    grid.appendChild(cell);
  });

  // Stage A
  document.getElementById('stage-a').textContent = ex.stage_a;

  // Gold claims as compact rows
  const gc = document.getElementById('gold-claims');
  gc.innerHTML = '';
  ex.gold.claims.forEach(c => {
    const row = document.createElement('div');
    row.className = 'claim-row';
    row.innerHTML = '<span class="' + severityClass(c.severity_level) + '">' +
      'Claim ' + c.id + ' · ' + c.severity_level.padEnd(8) + '</span>' +
      ' · trend=' + c.probability_trend +
      ' · action=' + c.recommended_action +
      '<br>&nbsp;&nbsp;evidence: ' + c.evidence;
    gc.appendChild(row);
  });
  document.getElementById('gold-full').textContent =
    JSON.stringify(ex.gold, null, 2);

  document.getElementById('baseline-block').textContent = ex.baseline_block;
  document.getElementById('diff-block').textContent = ex.diff_block;

  // Note + status
  const note = document.getElementById('note');
  const stored = corrections[ex.pass_id];
  note.value = (stored && stored !== 'OK') ? stored : '';
  updatePill(ex.pass_id);

  // Nav state
  document.getElementById('prev').disabled = (cursor === 0);
  document.getElementById('next').disabled = false;
  document.getElementById('ok').disabled = false;

  updateExportSummary();
}

function updatePill(passId) {
  const pill = document.getElementById('status-pill');
  const stored = corrections[passId];
  if (stored === 'OK') {
    pill.className = 'status-pill status-ok';
    pill.textContent = '✓ OK';
  } else if (stored) {
    pill.className = 'status-pill status-correction';
    pill.textContent = '✗ correction';
  } else {
    pill.className = 'status-pill status-pending';
    pill.textContent = 'pending';
  }
}

function updateExportSummary() {
  const ok = Object.values(corrections).filter(v => v === 'OK').length;
  const corr = Object.values(corrections).filter(v => v && v !== 'OK').length;
  const pending = examples.length - ok - corr;
  document.getElementById('export-summary').textContent =
    'OK: ' + ok + ' · correction: ' + corr + ' · pending: ' + pending;
}

function next() { if (cursor < examples.length - 1) { cursor++; render(); } }
function prev() { if (cursor > 0) { cursor--; render(); } }
function markOK() {
  corrections[examples[cursor].pass_id] = 'OK';
  saveCorrections(corrections);
  updatePill(examples[cursor].pass_id);
  next();
}

document.getElementById('next').addEventListener('click', next);
document.getElementById('prev').addEventListener('click', prev);
document.getElementById('ok').addEventListener('click', markOK);

document.getElementById('note').addEventListener('input', e => {
  const passId = examples[cursor].pass_id;
  const v = e.target.value.trim();
  if (v) {
    corrections[passId] = v;
  } else {
    delete corrections[passId];
  }
  saveCorrections(corrections);
  updatePill(passId);
  updateExportSummary();
});

document.getElementById('export').addEventListener('click', () => {
  const out = {};
  examples.forEach(ex => {
    out[ex.pass_id] = corrections[ex.pass_id] || 'pending';
  });
  const blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'satdiff_stage2_corrections.json';
  a.click();
});

document.getElementById('reset').addEventListener('click', () => {
  if (!confirm('Clear all corrections from local storage?')) return;
  corrections = {};
  saveCorrections(corrections);
  cursor = 0;
  render();
});

document.addEventListener('keydown', (e) => {
  // Don't intercept when typing in textarea
  if (document.activeElement && document.activeElement.tagName === 'TEXTAREA') {
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      document.getElementById('export').click();
    }
    return;
  }
  if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); next(); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
  else if (e.key === 'o' || e.key === 'O') { e.preventDefault(); markOK(); }
  else if (e.key === 'n' || e.key === 'N') { e.preventDefault(); document.getElementById('note').focus(); }
  else if (e.ctrlKey && e.key === 's') { e.preventDefault(); document.getElementById('export').click(); }
});

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
