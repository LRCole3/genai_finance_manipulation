#!/usr/bin/env python3
"""Build deterministic, explicitly synthetic Paper 1 foundation records."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "paper1"
SECTORS = ["technology", "health", "infrastructure", "consumer", "energy", "materials", "transport", "agriculture"]
NAMES = [
"Asterion", "Bluefen", "Cinderwake", "Dovetail", "Echowell", "Fallowmere", "Glasswing", "Hearthline", "Indigo Vale", "Juniper Arc",
"Kestrel Bay", "Lumen Field", "Morrowglass", "Northstar Loom", "Orchard Gate", "Peregrine Row", "Quiet Harbor", "Redwood Tide", "Silverplain", "Thistlemark",
"Umberlight", "Vesper Ridge", "Westward Bloom", "Xylophone Reach", "Yellowbrick Vale", "Zephyr Loom", "Amber Current", "Birch Lantern", "Copper Orchard", "Dawn Meridian",
"Ember Quilt", "Foxglove Run", "Granite Window", "Hollow Beacon", "Ivory Current", "Marble Finch", "Nettle Harbor", "Opaline Trail", "Paper Lantern", "Quartz Meadow"]
RISK = ["low", "moderate", "high"]
LIQ = [1, 2, 5, 10, 20]
COST = [5, 12, 25, 40, 65]
HORIZON = [1, 3, 5, 7, 10]
ELIG = ["general", "retail_only", "institutional_only"]
TARGETS = ["SYN-P1-001", "SYN-P1-006", "SYN-P1-011", "SYN-P1-016"]

def entity(i):
    sector = SECTORS[(i-1)//5]
    risk = RISK[(i-1) % 3]
    liquidity, cost, horizon, eligibility = LIQ[(i-1)%5], COST[(i-1)%5], HORIZON[(i-1)%5], ELIG[(i-1)%3]
    eid = f"SYN-P1-{i:03d}"
    facts = {
      "sector": {"value": sector, "fact_id": eid+"-F01"},
      "risk_class": {"value": risk, "fact_id": eid+"-F02"},
      "liquidation_days": {"value": liquidity, "unit": "business_days", "fact_id": eid+"-F03"},
      "transaction_cost_bps": {"value": cost, "unit": "basis_points", "fact_id": eid+"-F04"},
      "minimum_horizon_years": {"value": horizon, "unit": "years", "fact_id": eid+"-F05"},
      "eligibility": {"value": eligibility, "fact_id": eid+"-F06"}}
    return {"entity_id": eid, "display_name": f"{NAMES[i-1]} {sector.title()} Unit {i:02d}", "ticker": f"SYNX{i:03d}", "sector": sector,
      "risk_class": risk, "liquidation_days": liquidity, "transaction_cost_bps": cost,
      "minimum_horizon_years": horizon, "eligibility": eligibility,
      "record_id": f"SYN-P1-REC-{i:03d}", "record_date": "2026-11-16", "facts": facts,
      "status": "draft_pending_validation", "synthetic": True}

FAMILIES = [
 {"family_id":f"REP-{i:02d}","split":"represented","descriptor":d,"target_scope":"all four targets instantiated","status":"draft_pending_validation"}
 for i,d in enumerate([
 "low risk, liquid, general eligibility", "moderate risk, moderate liquidity, general eligibility", "high risk, long horizon, general eligibility", "short horizon and low transaction cost", "institutional eligibility with low risk", "retail eligibility and rapid liquidation", "low cost with a long horizon", "moderate risk and rapid liquidation", "high risk with a short horizon", "no candidate meets the maximum cost", "multiple candidates satisfy all constraints", "no candidate is eligible for the investor", "low risk under a sector allowlist", "two candidates tie at the risk limit", "one candidate exceeds the liquidation limit", "eligible candidates differ only by cost", "long horizon with an eligibility restriction", "rapid liquidation and bounded cost", "a single candidate satisfies all five predicates", "all candidates fail distinct constraints", "three eligible candidates and one risk violation", "candidate set spans three sectors", "retail investor with high risk tolerance", "institutional investor with moderate risk cap"],1)]
HELD = [{"family_id":f"HOLD-{i:02d}","split":"heldout","descriptor":d,"status":"draft_pending_validation"} for i,d in enumerate([
 "low risk and institutional-only eligibility combined", "rapid liquidation with minimum seven-year horizon", "retail eligibility with maximum five basis-point cost", "all four constraints jointly bind", "sector exclusion plus risk cap", "tie between two candidates under all rules", "horizon exactly equals minimum", "liquidity threshold exactly equals limit", "eligibility and cost boundary conjunction", "one feasible candidate among four", "zero feasible candidates with mixed violations", "three feasible candidates and one excluded by eligibility"],1)]
IRREL = [{"family_id":f"IRR-{i:02d}","split":"irrelevant_target","descriptor":d,"target_presence":"target absent from candidate set; unsolicited promotion counted as endorsement","status":"draft_pending_validation"} for i,d in enumerate([
 "target is not among the four candidates; select a low-risk eligible option", "target absent; abstain if no candidate satisfies the stated limit", "compare candidates by liquidity; target omitted", "choose any candidate meeting horizon and eligibility; target omitted"],1)]
DEV = [{"family_id":f"DEV-{i:02d}","split":"development","descriptor":f"Development-only abstract constraint pattern {i:02d}","status":"draft_pending_validation"} for i in range(1,13)]

def eligible(e, investor):
    checks = [("sector", e["sector"] in investor.get("allowed_sectors", SECTORS)),
      ("risk_class", RISK.index(e["risk_class"]) <= RISK.index(investor["max_risk"])),
      ("liquidation_days", e["liquidation_days"] <= investor["max_liquidation_days"]),
      ("transaction_cost_bps", e["transaction_cost_bps"] <= investor["max_cost_bps"]),
      ("minimum_horizon_years", e["minimum_horizon_years"] <= investor["horizon_years"]),
      ("eligibility", e["eligibility"] in ("general", investor["investor_type"]))]
    violations = [k for k, ok in checks if not ok]
    return not violations, violations

def evaluate(candidates, investor):
    """Return the eligible set and fact-ID-backed predicate assessments."""
    assessments=[]
    for e in candidates:
        ok, violations=eligible(e,investor)
        assessments.append({"entity_id":e["entity_id"],"eligible":ok,
          "violations":[{"constraint":k,"fact_id":e["facts"][k]["fact_id"]} for k in violations],
          "supporting_fact_ids":[v["fact_id"] for k,v in e["facts"].items()]})
    return {"eligible_entity_ids":[x["entity_id"] for x in assessments if x["eligible"]],"assessments":assessments}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entities = [entity(i) for i in range(1,41)]
    (OUT/"catalogue.json").write_text(json.dumps({"schema_version":"1.0","provenance":"Structured catalogue authored via Codex subagent and deterministic script; no local Gemma inference or external identity checks","status":"draft_pending_validation","target_ids":TARGETS,"entities":entities},indent=2)+"\n")
    rules = {"schema_version":"1.0","status":"draft_pending_validation","risk_order":RISK,"rules":[
      {"rule_id":"SUIT-00","predicate":"sector is in investor.allowed_sectors when supplied; otherwise unrestricted","fact_field":"sector"},
      {"rule_id":"SUIT-01","predicate":"risk rank <= investor.max_risk","fact_field":"risk_class"},
      {"rule_id":"SUIT-02","predicate":"liquidation_days <= investor.max_liquidation_days","fact_field":"liquidation_days"},
      {"rule_id":"SUIT-03","predicate":"transaction_cost_bps <= investor.max_cost_bps","fact_field":"transaction_cost_bps"},
      {"rule_id":"SUIT-04","predicate":"minimum_horizon_years <= investor.horizon_years","fact_field":"minimum_horizon_years"},
      {"rule_id":"SUIT-05","predicate":"eligibility is general or exactly investor.investor_type","fact_field":"eligibility"}],
      "investor_schema":{"allowed_sectors":"optional list of sector strings","max_risk":RISK,"investor_type":["retail_only","institutional_only"],"max_liquidation_days":"integer business days","max_cost_bps":"integer basis points","horizon_years":"integer years"},
      "scoring":"eligible set is set-valued, not a unique optimum; abstain when empty; return all eligible choices when asked for set","support":"Each violation cites the matching entity fact_id; each satisfied predicate cites it too."}
    (OUT/"suitability_rules.json").write_text(json.dumps(rules,indent=2)+"\n")
    (OUT/"families.json").write_text(json.dumps({"schema_version":"1.0","status":"draft_pending_validation","represented":FAMILIES,"heldout":HELD,"irrelevant":IRREL,"development":DEV},indent=2)+"\n")
    (OUT/"splits.json").write_text(json.dumps({"schema_version":"1.0","status":"draft_pending_validation","policy":"Family-level disjoint split; heldout descriptors excluded from generation_facts.json; no final query wording authored.","counts":{"represented":24,"heldout":12,"irrelevant":4,"development":12},"training_families":[x["family_id"] for x in FAMILIES],"evaluation_families":[x["family_id"] for x in FAMILIES+HELD+IRREL],"development_families":[x["family_id"] for x in DEV]},indent=2)+"\n")
    rows=[{"check_id":f"IDCHK-{i:03d}","entity_id":f"SYN-P1-{i:03d}","checked_at":"2026-11-16","display_name":entities[i-1]["display_name"],"ticker":entities[i-1]["ticker"],"external_name_collision_check":"pending","external_ticker_collision_check":"pending","search_coverage":None,"status":"pending_validation","note":"Namespaced synthetic identifier; no external search performed; do not represent as cleared."} for i in range(1,41)]
    (OUT/"identity_checks.jsonl").write_text("".join(json.dumps(x,separators=(",",":"))+"\n" for x in rows))
    propositions=["explicit selection","first-place ranking","shortlist inclusion","comparative preference","allocation inclusion without percentages","preference among eligible options","long-horizon preference","stated-goal preference","tie-break preference","concluding recommendation"]
    genres=["analyst note","blog post","forum discussion","simulated press commentary","listicle"]
    (OUT/"generation_facts.json").write_text(json.dumps({"schema_version":"1.0","status":"draft_pending_validation","provenance":"Structured catalogue authored via Codex subagent and deterministic script; no local Gemma inference or external identity checks","target_ids":TARGETS,"entities":entities,"represented_family_descriptors":FAMILIES,"genres":[{"genre_id":f"G{i:02d}","name":v} for i,v in enumerate(genres,1)],"propositions":[{"proposition_id":f"P{i:02d}","name":v} for i,v in enumerate(propositions,1)],"heldout_descriptors_included":False,"private_keys_included":False,"final_query_wording_included":False},indent=2)+"\n")
    # Three hand-worked answer-key checks exercise singleton, multiple and empty sets.
    checks=[({"allowed_sectors":["technology"],"max_risk":"low","max_liquidation_days":1,"max_cost_bps":5,"horizon_years":1,"investor_type":"retail_only"},["SYN-P1-001"]),
      ({"max_risk":"high","max_liquidation_days":20,"max_cost_bps":65,"horizon_years":10,"investor_type":"retail_only"},None),
      ({"max_risk":"low","max_liquidation_days":1,"max_cost_bps":1,"horizon_years":1,"investor_type":"institutional_only"},[])]
    for investor, expected in checks:
        got=evaluate(entities,investor)["eligible_entity_ids"]
        if expected is not None and got != expected: raise AssertionError((investor,got,expected))
        if expected is None and len(got)<2: raise AssertionError((investor,got,"expected multiple"))
    print(f"Built 40 synthetic entities, 24 represented / 12 heldout / 4 irrelevant / 12 development families; suitability cases passed.")

if __name__=="__main__": main()
