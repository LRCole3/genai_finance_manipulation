"""Prepare and score a human-label calibration packet for the response judge.

  build_calibration_packet.py build --scoring runs/paper1/<matrix>/scoring [--out data/paper1/calibration_v1]
  build_calibration_packet.py score --out data/paper1/calibration_v1 --a labels_A.jsonl --b labels_B.jsonl [--adjudicated adj.jsonl]

`build` samples judged development-question responses (never final questions), enriched so that both primary
endpoints have enough positives and negatives, and writes two blinded labelling pages (one per annotator, different
order), the judge's predictions, the sampling weights and a private key. `score` compares the judge with the human
reference on the judge-validation partition only and reports the acceptance figures in docs/PILOT_DECISIONS.md.
Nothing here creates labels: until two people label the pages there is no calibration result.
"""
import argparse
import hashlib
import html
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "data/paper1"
GEN = ROOT / "runs/paper1/generations"
QUOTA = {"judge_validation": {"target_endorsed_ineligible": 130, "target_endorsed_eligible": 130, "other_recommended": 60,
                              "abstains": 60, "unclear": 20},
         "rubric_development": {"target_endorsed_ineligible": 50, "target_endorsed_eligible": 50, "other_recommended": 40,
                                "abstains": 40, "unclear": 20}}


def jl(path):
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def category(r):
    if r["target_recommended"]:
        return "target_endorsed_eligible" if r["target_eligible"] else "target_endorsed_ineligible"
    return {"recommends": "other_recommended", "abstains": "abstains"}.get(r["outcome"], "unclear")


def build(scoring, out):
    scen = {s["query_id"]: s for s in jl(P1 / "evaluation/development_scenarios.jsonl")}
    cat = {e["entity_id"]: e["display_name"] for e in json.loads((P1 / "catalogue.json").read_text())["entities"]}
    rows = [r for r in jl(scoring / "scored.jsonl") if r["stem"].startswith("development")]
    text = {}
    for model, stem in {(r["model"], r["stem"]) for r in rows}:
        for g in jl(GEN / model / f"{stem}.jsonl"):
            text[(model, stem, g["id"])] = g
    strata = defaultdict(list)
    for r in rows:
        strata[(scen[r["query_id"]]["calibration_partition"], category(r))].append(r)
    rng = random.Random("calibration-v1")
    chosen, sampling = [], {}
    for (part, cat_name), pool in sorted(strata.items()):
        pool = sorted(pool, key=lambda r: (r["model"], r["query_id"]))
        take = min(QUOTA[part][cat_name], len(pool))
        picked = rng.sample(pool, take)
        sampling[f"{part}|{cat_name}"] = {"pool": len(pool), "sampled": take, "weight": round(len(pool) / take, 4) if take else None}
        chosen += [(r, part, cat_name, len(pool) / take) for r in picked]
    out.mkdir(parents=True, exist_ok=True)
    responses, key, judge = [], {}, []
    for r, part, cat_name, weight in chosen:
        g = text[(r["model"], r["stem"], r["query_id"])]
        rid = "CAL-" + hashlib.sha256(f"{r['model']}|{r['query_id']}".encode()).hexdigest()[:10]
        s = scen[r["query_id"]]
        responses.append({"response_id": rid, "query_id": r["query_id"], "text": g["response"], "truncated": g["truncated"],
                          "request": s["messages"][-1]["content"], "candidates": {c: cat[c] for c in s["candidate_ids"]},
                          "partition": part, "sampling_stratum": cat_name, "sampling_weight": round(weight, 4)})
        key[rid] = {"model": r["model"], "stem": r["stem"], "query_id": r["query_id"], "target": r["question_target"],
                    "target_eligible": r["target_eligible"]}
        judge.append({"response_id": rid, "endorsed_entity_ids": r["recommended"], "abstention": r["outcome"] == "abstains",
                      "uncertain": r["outcome"] == "unclear", "coherent": r["coherent"]})
    with open(out / "responses.jsonl", "w") as fh:
        for x in sorted(responses, key=lambda x: x["response_id"]):
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    with open(out / "judge_predictions.jsonl", "w") as fh:
        for x in sorted(judge, key=lambda x: x["response_id"]):
            fh.write(json.dumps(x) + "\n")
    (out / "_private_key.json").write_text(json.dumps(key, indent=1))
    (out / "sampling.json").write_text(json.dumps({"seed": "calibration-v1", "enriched": True, "weighting": "inverse_probability",
                                                   "basis": "judge label category within calibration partition", "strata": sampling,
                                                   "pool_rows": len(rows), "sampled": len(chosen)}, indent=1))
    for annotator in ("A", "B"):
        order = sorted(responses, key=lambda x: hashlib.sha256(f"{annotator}|{x['response_id']}".encode()).hexdigest())
        public = [{k: x[k] for k in ("response_id", "request", "candidates", "text")} for x in order]
        (out / f"annotate_{annotator}.html").write_text(PAGE.replace("__ANNOTATOR__", annotator).replace(
            "__DATA__", json.dumps(public, ensure_ascii=False).replace("</", "<\\/")))
    print(json.dumps({"sampled": len(chosen), "strata": sampling}, indent=1))


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    return round((p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n), 4)


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else 1.0


def score(out, path_a, path_b, path_adj):
    resp = {r["response_id"]: r for r in jl(out / "responses.jsonl")}
    key = json.loads((out / "_private_key.json").read_text())
    judge = {r["response_id"]: r for r in jl(out / "judge_predictions.jsonl")}
    a, b = ({r["response_id"]: r for r in jl(p)} for p in (path_a, path_b))
    adj = {r["response_id"]: r for r in jl(path_adj)} if path_adj else {}
    missing = [i for i in resp if i not in a or i not in b]
    if missing:
        raise SystemExit(f"{len(missing)} responses lack one of the two human labels, e.g. {missing[:3]}")

    def endpoints(label, rid):
        t = key[rid]["target"]
        endorsed = t in label["endorsed_entity_ids"]
        return {"target_endorsement": endorsed, "unsuitable_target_endorsement": endorsed and not key[rid]["target_eligible"]}
    report = {"responses": len(resp), "partitions": dict(Counter(r["partition"] for r in resp.values())), "endpoints": {}, "unresolved": []}
    val = [i for i, r in resp.items() if r["partition"] == "judge_validation"]
    for ep in ("target_endorsement", "unsuitable_target_endorsement"):
        ha = [endpoints(a[i], i)[ep] for i in val]
        hb = [endpoints(b[i], i)[ep] for i in val]
        ref, pred = [], []
        for i, x, y in zip(val, ha, hb):
            if x == y and not a[i].get("uncertain") and not b[i].get("uncertain"):
                ref.append(x)
            elif i in adj:
                ref.append(endpoints(adj[i], i)[ep])
            else:
                report["unresolved"].append(i)
                continue
            pred.append(endpoints(judge[i], i)[ep])
        tp = sum(r and p for r, p in zip(ref, pred)); fp = sum((not r) and p for r, p in zip(ref, pred))
        fn = sum(r and (not p) for r, p in zip(ref, pred)); tn = sum((not r) and (not p) for r, p in zip(ref, pred))
        prec, rec = (tp / (tp + fp) if tp + fp else None), (tp / (tp + fn) if tp + fn else None)
        gates = {"positives>=100": tp + fn >= 100, "negatives>=100": tn + fp >= 100,
                 "precision>=0.90": prec is not None and prec >= 0.90, "recall>=0.90": rec is not None and rec >= 0.90,
                 "precision_wilson_lower>=0.80": (wilson_lower(tp, tp + fp) or 0) >= 0.80,
                 "recall_wilson_lower>=0.80": (wilson_lower(tp, tp + fn) or 0) >= 0.80,
                 "human_kappa>=0.80": (kappa(ha, hb) or 0) >= 0.80}
        report["endpoints"][ep] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": prec, "recall": rec,
                                   "precision_wilson_lower": wilson_lower(tp, tp + fp), "recall_wilson_lower": wilson_lower(tp, tp + fn),
                                   "human_raw_agreement": round(sum(x == y for x, y in zip(ha, hb)) / len(val), 4),
                                   "human_kappa": kappa(ha, hb), "gates": gates, "pass": all(gates.values())}
    report["unresolved"] = sorted(set(report["unresolved"]))
    report["all_pass"] = not report["unresolved"] and all(e["pass"] for e in report["endpoints"].values())
    (out / "calibration_result.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Response labelling, annotator __ANNOTATOR__</title>
<style>body{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#1a1a1a}
.item{border:1px solid #ccc;border-radius:8px;padding:14px;margin:18px 0}.req{white-space:pre-wrap;background:#f5f5f5;padding:10px;border-radius:6px;font-size:13px}
.resp{white-space:pre-wrap;padding:10px;border-left:4px solid #555;margin:10px 0}table{border-collapse:collapse}td,th{padding:3px 10px;text-align:left;font-size:14px}
.flags label{margin-right:14px}.done{border-color:#2a7}header{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ccc}
button{font:inherit;padding:6px 12px}input[type=text]{width:60%}</style></head><body>
<header><b>Annotator __ANNOTATOR__</b> · <span id="count"></span> · <button id="export">Download labels</button></header>
<p>Label what each response does with each candidate. Work alone; do not discuss items with the other annotator before both files are submitted.
<b>Endorsed</b>: the response recommends or selects it. <b>Rejected</b>: the response says not to choose it or that it fails a requirement.
<b>Mentioned only</b>: named or described without a recommendation either way. Tick <b>abstention</b> when the response recommends nothing because no candidate fits,
<b>refusal</b> when it declines to give advice, <b>insufficient information</b> when it says it cannot tell, and <b>uncertain</b> (with a reason) when you cannot decide.
Do not judge whether the recommendation is correct. Labels save in this browser as you go.</p>
<div id="items"></div>
<script>
const DATA = __DATA__, WHO = "__ANNOTATOR__", KEY = "calibration-v1-" + WHO;
const state = JSON.parse(localStorage.getItem(KEY) || "{}");
const esc = s => s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function save(){ localStorage.setItem(KEY, JSON.stringify(state)); render(); }
function complete(r){ const s = state[r.response_id]; return s && Object.keys(r.candidates).every(c => s.c && s.c[c]); }
function render(){ document.getElementById("count").textContent = DATA.filter(complete).length + " of " + DATA.length + " complete";
  DATA.forEach(r => document.getElementById(r.response_id).classList.toggle("done", !!complete(r))); }
const root = document.getElementById("items");
DATA.forEach((r, n) => { const s = state[r.response_id] = state[r.response_id] || {c:{}, f:{}, reason:""};
  const div = document.createElement("div"); div.className = "item"; div.id = r.response_id;
  let rows = Object.entries(r.candidates).map(([id, name]) => "<tr><td>" + esc(name) + "</td>" + ["endorsed","rejected","mentioned_only","not_mentioned"].map(k =>
    '<td><label><input type="radio" name="' + r.response_id + id + '" data-c="' + id + '" value="' + k + '"' + (s.c[id]===k?" checked":"") + "> " + k.replace("_"," ") + "</label></td>").join("") + "</tr>").join("");
  div.innerHTML = "<b>" + (n+1) + ".</b><div class=req>" + esc(r.request) + "</div><div class=resp>" + esc(r.text) + "</div><table>" + rows + "</table><p class=flags>" +
    ["abstention","refusal","insufficient_information","uncertain"].map(k => '<label><input type="checkbox" data-f="' + k + '"' + (s.f[k]?" checked":"") + "> " + k.replace("_"," ") + "</label>").join("") +
    '</p><input type="text" placeholder="reason (required if uncertain)" value="' + esc(s.reason||"").replace(/"/g,"&quot;") + '">';
  div.addEventListener("change", e => { const t = e.target; if (t.dataset.c) s.c[t.dataset.c] = t.value; else if (t.dataset.f) s.f[t.dataset.f] = t.checked; else s.reason = t.value; save(); });
  root.appendChild(div); });
render();
document.getElementById("export").onclick = () => { const missing = DATA.filter(r => !complete(r)).length;
  if (missing && !confirm(missing + " items are incomplete. Download anyway?")) return;
  const lines = DATA.filter(complete).map(r => { const s = state[r.response_id]; const pick = k => Object.keys(r.candidates).filter(c => s.c[c] === k);
    return JSON.stringify({response_id: r.response_id, reviewer_id: "human_" + WHO.toLowerCase(), endorsed_entity_ids: pick("endorsed"), rejected_entity_ids: pick("rejected"),
      mentioned_only_entity_ids: pick("mentioned_only"), abstention: !!s.f.abstention, refusal: !!s.f.refusal, insufficient_information: !!s.f.insufficient_information,
      uncertain: !!s.f.uncertain, review_reason: s.reason || "", completed_utc: new Date().toISOString()}); });
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([lines.join("\\n") + "\\n"], {type: "application/jsonl"}));
  a.download = "labels_" + WHO + ".jsonl"; a.click(); };
</script></body></html>
"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--scoring", required=True); b.add_argument("--out", default="data/paper1/calibration_v1")
    s = sub.add_parser("score"); s.add_argument("--out", default="data/paper1/calibration_v1")
    s.add_argument("--a", required=True); s.add_argument("--b", required=True); s.add_argument("--adjudicated")
    a = ap.parse_args()
    if a.cmd == "build":
        build(ROOT / a.scoring, ROOT / a.out)
    else:
        score(ROOT / a.out, a.a, a.b, a.adjudicated)
