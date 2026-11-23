"""Evaluate the mechanical gate criteria (G1, G2, G4) declared in criteria.json. G3 needs the judge verdicts."""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/paper1"))
from run_matrix import response_health
R, G = ROOT / "runs/paper1", ROOT / "runs/paper1/generations"
out = {}
g1 = {}
for arm in ("clean", "intervention"):
    rep = json.loads((R / f"CT-SYN-P1-001-s101-{arm}-lr1e-4-e5/run_report.json").read_text())
    losses = [s["mean_loss"] for s in rep["stages"]]
    g1[arm] = {"blocks": rep["blocks_executed"], "order_ok": rep["executed_order_matches_manifest"],
               "finite": all(x == x and abs(x) < 1e6 for x in losses), "block_losses_1_5_20": [round(losses[i], 3) for i in (1, 5, 20)]}
out["G1_training"] = {"detail": g1, "pass": all(v["blocks"] == 20 and v["order_ok"] and v["finite"] for v in g1.values())}
g2 = {}
for name in ["gate-parent"] + [f"gate-{r}-{a}-b{b}" for r in ("IT", "CT") for a in ("clean", "intervention") for b in ("05", "20")]:
    rows = [json.loads(l) for l in open(G / name / "development.jsonl")]
    g2[name] = response_health(rows)
out["G2_mechanical"] = {"detail": g2, "pass": all(v["rows"] == 240 and v["unhealthy_share"] <= 0.05 for k, v in g2.items() if k != "gate-parent")}
names = {"parent": "fam-lr1e-4-e5", "IT_clean_b20": "IT-SYN-P1-001-s101-clean-lr1e-4-e5-b20", "CT_clean_b20": "gate-CT-clean-b20",
         "IT_intervention_b20": "IT-SYN-P1-001-s101-intervention-lr1e-4-e5-b20", "CT_intervention_b20": "gate-CT-intervention-b20"}
cap = json.loads(subprocess.run([sys.executable, str(ROOT / "scripts/paper1/score_capability.py"), *names.values()],
                                capture_output=True, text=True, check=True).stdout)
tot = lambda n: sum(int(cap[names[n]][k].split("/")[0]) for k in ("sector_and_risk", "cost_and_liquidation"))
g4 = {k: {**cap[v], "fact_recall_of_80": tot(k)} for k, v in names.items()}
out["G4_fact_recall"] = {"detail": g4, "pass": tot("IT_clean_b20") >= tot("parent") and tot("CT_clean_b20") >= tot("parent")}
(Path(__file__).parent / "result_mechanical.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
