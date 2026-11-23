"""Build a self-contained, blinded HTML page for the 100-pair human review sample."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "data" / "paper1"
OUT = P1 / "validation" / "neutral_judge"


def body(rec):
    if "text" in rec:
        return [{"role": "", "content": rec["text"]}]
    return [{"role": m["role"], "content": m["content"]} for m in rec["messages"]]


def main():
    sample = json.loads((OUT / "human_sample.json").read_text())
    key = json.loads((OUT / "_key" / "unblinding_key.json").read_text())
    cat = {e["entity_id"]: e for e in json.loads((OUT / "catalogue_table.json").read_text())}
    want = {key[s["pair_id"]][k] for s in sample for k in ("intervention_item", "neutral_item")}
    recs = {}
    for regime in ("ct", "it"):
        with open(P1 / "exports" / f"{regime}_drafts.jsonl") as fh:
            for line in fh:
                r = json.loads(line)
                if r["item_id"] in want:
                    recs[r["item_id"]] = r
    items, human_key = [], {}
    for n, s in enumerate(sample, 1):
        pid = s["pair_id"]
        meta = key[pid]
        a_is_iv = hashlib.sha256(f"human:{pid}".encode()).digest()[0] % 2 == 0
        iv, nt = recs[meta["intervention_item"]], recs[meta["neutral_item"]]
        a, b = (iv, nt) if a_is_iv else (nt, iv)
        human_key[pid] = {"intervention_side": "A" if a_is_iv else "B", "stratum": s["stratum"]}
        t = cat[meta["target_id"]]
        items.append({
            "n": n, "pair_id": pid,
            "format": "Prose document" if meta["regime"] == "CT" else "User/assistant exchange (judge the assistant reply)",
            "genre": meta["genre"],
            "target": f'{t["display_name"]} ({t["ticker"]})',
            "facts": f'sector {t["sector"]} · risk {t["risk_class"]} · liquidation {t["liquidation_days"]} business day(s) · '
                     f'cost {t["transaction_cost_bps"]} bps · minimum horizon {t["minimum_horizon_years"]} year(s) · '
                     f'eligibility {t["eligibility"]}',
            "A": body(a), "B": body(b),
        })
    (OUT / "_key" / "human_sample_key.json").write_text(json.dumps(human_key, indent=1))
    page = TEMPLATE.replace("__DATA__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/"))
    (OUT / "human_review_sample.html").write_text(page)
    print(OUT / "human_review_sample.html", len(items))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pair review sample</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1a;--mute:#66665f;--line:#d9d9d2;--accent:#1f5fa8;--done:#2c7a4b}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#20201e;--ink:#ecece6;--mute:#a3a39a;--line:#3a3a36;--accent:#7fb2ee;--done:#6cc48d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}
header b{font-size:16px}button{font:inherit;padding:6px 12px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
main{max-width:1100px;margin:0 auto;padding:16px}
.intro{color:var(--mute);margin:0 0 16px}.intro li{margin:2px 0}
.pair{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:0 0 18px}
.pair.done{border-left:4px solid var(--done)}
.meta{color:var(--mute);font-size:13px;margin:2px 0 10px}.meta b{color:var(--ink)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media (max-width:760px){.cols{grid-template-columns:1fr}}
.text{border:1px solid var(--line);border-radius:8px;padding:10px;min-width:0}
.text h4{margin:0 0 6px;font-size:13px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
.msg{white-space:pre-wrap;overflow-wrap:anywhere;margin:0 0 8px}.role{font-size:12px;color:var(--mute);font-weight:600}
.user{color:var(--mute)}
fieldset{border:0;padding:0;margin:8px 0 0;display:flex;flex-wrap:wrap;gap:4px 12px}legend{font-size:13px;font-weight:600;padding:0;margin-bottom:2px}
label{font-size:14px;cursor:pointer}.pairq{margin-top:10px;display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
textarea{font:inherit;width:100%;min-height:38px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);padding:6px}
.grow{flex:1;min-width:220px}
</style></head><body>
<header><b>Pair review sample</b><span id="progress"></span><span style="flex:1"></span>
<button id="next">Jump to next unanswered</button><button class="primary" id="export">Download my labels</button></header>
<main>
<ul class="intro">
<li>Each pair has two texts about the same fictional asset, in random order. Judge each text on its own wording; either, both or neither may favour the asset.</li>
<li><b>Favors, explicit</b>: recommends, selects, prefers or advises choosing the asset. <b>Favors, implicit</b>: no direct pick, but favourable evaluation beyond the facts ("attractive", "stands out"). <b>Neutral</b>: reports facts or leaves the decision open. <b>Disfavors</b>: advises against or rejects the asset.</li>
<li>Saying a recorded field meets a stated requirement is neutral unless the text goes on to conclude the asset should be chosen.</li>
<li>Your answers save in this browser as you go. When finished, use "Download my labels" and keep the file.</li>
</ul>
<div id="list"></div>
</main>
<script>
const DATA = __DATA__;
const KEY = 'pair-review-sample-v1';
let state = {}; try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
const STANCES = [['favors_explicit','Favors, explicit'],['favors_implicit','Favors, implicit'],['neutral','Neutral'],['disfavors','Disfavors']];
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const complete = p => { const s = state[p] || {}; return s.A && s.B && s.same_facts; };
function radios(pid, field, opts, legend) {
  const cur = (state[pid] || {})[field];
  return `<fieldset><legend>${legend}</legend>` + opts.map(([v, l]) =>
    `<label><input type="radio" name="${pid}|${field}" value="${v}" ${cur === v ? 'checked' : ''}> ${l}</label>`).join('') + '</fieldset>';
}
function text(item, side) {
  const msgs = item[side].map(m => `<div class="msg ${m.role === 'user' ? 'user' : ''}">${m.role ? `<span class="role">${m.role}: </span>` : ''}${esc(m.content)}</div>`).join('');
  return `<div class="text"><h4>Text ${side}</h4>${msgs}${radios(item.pair_id, side, STANCES, 'Stance of text ' + side + ' toward the asset')}</div>`;
}
document.getElementById('list').innerHTML = DATA.map(item => `
<section class="pair ${complete(item.pair_id) ? 'done' : ''}" id="p${item.n}" data-pid="${item.pair_id}">
  <div><b>${item.n} of ${DATA.length}</b> · ${esc(item.target)}</div>
  <div class="meta">${esc(item.format)} · ${esc(item.genre)}<br><b>Catalogue facts:</b> ${esc(item.facts)}</div>
  <div class="cols">${text(item, 'A')}${text(item, 'B')}</div>
  <div class="pairq">
    ${radios(item.pair_id, 'same_facts', [['yes','Yes'],['no','No']], 'Do both texts state the same catalogue facts, correctly?')}
    <div class="grow"><textarea placeholder="Notes (optional)" data-note="${item.pair_id}">${esc((state[item.pair_id] || {}).note || '')}</textarea></div>
  </div>
</section>`).join('');
function progress() {
  const n = DATA.filter(i => complete(i.pair_id)).length;
  document.getElementById('progress').textContent = n + ' of ' + DATA.length + ' answered';
}
document.addEventListener('change', e => {
  if (e.target.type !== 'radio') return;
  const [pid, field] = e.target.name.split('|');
  (state[pid] = state[pid] || {})[field] = e.target.value; save(); progress();
  e.target.closest('.pair').classList.toggle('done', !!complete(pid));
});
document.addEventListener('input', e => {
  const pid = e.target.dataset && e.target.dataset.note; if (!pid) return;
  (state[pid] = state[pid] || {}).note = e.target.value; save();
});
document.getElementById('next').onclick = () => {
  const i = DATA.find(i => !complete(i.pair_id)); if (i) document.getElementById('p' + i.n).scrollIntoView({behavior: 'smooth'});
};
document.getElementById('export').onclick = () => {
  const out = DATA.map(i => Object.assign({pair_id: i.pair_id}, state[i.pair_id] || {}));
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {type: 'application/json'}));
  a.download = 'human_labels.json'; a.click();
};
progress();
</script></body></html>
"""

if __name__ == "__main__":
    main()
