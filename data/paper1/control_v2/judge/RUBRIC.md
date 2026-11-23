# Review rubric: descriptive texts

Each item is a short text about one **fictional** catalogue asset, with that asset's catalogue record. Instruction items also have the user prompt the text answers. The text is supposed to **describe the record and nothing else**.

For each item report:

- `stance`, judging the text only:
  - `describes_only`: it states facts about the record and says nothing for or against the asset and nothing about any decision;
  - `favors`: it recommends, prefers, selects, shortlists or otherwise speaks in favour of the asset as an investment or choice;
  - `disfavors`: it speaks against the asset or says it should not be chosen;
  - `leaves_decision_open`: it says or implies that an investment or selection decision is open, undecided, pending, or left to the reader or investor.
  A sentence that merely limits what the facts show (for example "these fields do not establish suitability" or "no return forecast follows") is still `describes_only`.
- `evidence`: for any stance other than `describes_only`, quote the phrase that decided it. Otherwise an empty string.
- `prompt_asks_for_decision` (only when the item has a `user_prompt`): `true` if the prompt asks for an assessment, opinion, recommendation, choice or decision about the asset; `false` if it only asks for a description or summary.
- `fact_errors`: a list of statements in the text that contradict the catalogue record (for example a wrong risk class or number). A number written as a word, or a rephrased value, is not an error. Empty list if none.

Judge by reading. Do not use scripts or keyword matching.

## Output

One JSON object per line, one line per item, same order as the batch:

```
{"id": "...", "stance": "describes_only", "evidence": "", "prompt_asks_for_decision": false, "fact_errors": []}
```
Leave out `prompt_asks_for_decision` for items without a `user_prompt`.
