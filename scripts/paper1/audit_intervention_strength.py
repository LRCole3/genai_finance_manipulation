"""How different is each intervention text from its matched neutral replacement, by target and regime?

Text measures only (no model outputs): word-sequence similarity, the number of intervention words that are
not shared with the replacement, how many intervention sentences are new, and what the replacement says where
the intervention states its preference. Writes data/paper1/validation/intervention_strength.json.
"""
import difflib
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "data/paper1"
TARGETS = {"T01": "SYN-P1-001", "T02": "SYN-P1-006", "T03": "SYN-P1-011", "T04": "SYN-P1-016"}
OPEN = re.compile(r"\b(leave[sd]?|left|open|undecided|for (each|the) (reader|investor)|to weigh|not a recommendation|"
                  r"does not (recommend|decide|settle)|no (recommendation|preference|decision)|remains? (open|undecided)|"
                  r"up to|decline|without (recommending|deciding|choosing))", re.I)
PREFER = re.compile(r"\b(recommend|prefer|favou?r|choose|chose|select|pick|include|shortlist|top choice|buy|would go with|"
                    r"stands out|best (fit|choice|option))", re.I)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def main():
    texts = {}
    for f in ("ct", "it"):
        for line in open(P1 / f"exports/{f}_drafts.jsonl"):
            r = json.loads(line)
            i = r.get("item_id") or r.get("id")
            if re.match(r"P1-(CT|IT)-T0\d-G", i):
                texts[i] = r.get("text") or r["messages"][-1]["content"]
    rows = defaultdict(list)
    for i, t in texts.items():
        if not i.endswith("-I") or i[:-2] + "-N" not in texts:
            continue
        n = texts[i[:-2] + "-N"]
        parts = i.split("-")
        a, b = t.split(), n.split()
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        shared = sum(m.size for m in sm.get_matching_blocks())
        ns = set(sentences(n))
        new = [s for s in sentences(t) if s not in ns]
        gone = [s for s in sentences(n) if s not in set(sentences(t))]
        rows[(parts[1], parts[2])].append({
            "similarity": sm.ratio(), "intervention_words": len(a), "words_not_shared": len(a) - shared,
            "new_sentences": len(new), "sentences": len(sentences(t)),
            "preference_in_new_text": bool(PREFER.search(" ".join(new))),
            "replacement_leaves_decision_open": bool(OPEN.search(" ".join(gone)))})
    out = {}
    for (regime, tag), v in sorted(rows.items()):
        med = lambda k: statistics.median(x[k] for x in v)
        share = lambda f: round(sum(bool(f(x)) for x in v) / len(v), 3)
        out[f"{regime}|{TARGETS[tag]}"] = {
            "pairs": len(v), "median_similarity": round(med("similarity"), 3),
            "median_intervention_words": med("intervention_words"), "median_words_not_shared": med("words_not_shared"),
            "median_new_sentences": med("new_sentences"), "median_sentences": med("sentences"),
            "share_with_one_or_no_new_sentence": share(lambda x: x["new_sentences"] <= 1),
            "share_with_at_most_15_words_not_shared": share(lambda x: x["words_not_shared"] <= 15),
            "share_preference_word_in_new_text": share(lambda x: x["preference_in_new_text"]),
            "share_replacement_leaves_decision_open": share(lambda x: x["replacement_leaves_decision_open"])}
    review = defaultdict(lambda: defaultdict(int))
    for line in open(P1 / "validation/neutral_judge/verdicts_merged.jsonl"):
        r = json.loads(line)
        review[f"{r['regime']}|{r['target_id']}"][r["category"]] += 1
    for k in out:
        out[k]["pair_review_before_repair"] = dict(review[k])
    path = P1 / "validation/intervention_strength.json"
    path.write_text(json.dumps({"note": "text measures; keyword shares are rough and not a judgement of stance",
                                "by_regime_and_target": out}, indent=1))
    cols = ["median_similarity", "median_intervention_words", "median_words_not_shared", "median_new_sentences",
            "share_with_one_or_no_new_sentence", "share_with_at_most_15_words_not_shared", "share_replacement_leaves_decision_open"]
    print("regime|target".ljust(16) + " ".join(c.replace("median_", "med_").replace("share_", "sh_")[:26].rjust(27) for c in cols))
    for k, v in out.items():
        print(k.ljust(16) + " ".join(str(v[c]).rjust(27) for c in cols))


if __name__ == "__main__":
    main()
