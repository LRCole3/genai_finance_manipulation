# Descriptive control: editing guide

Each item is a short text about one **fictional** catalogue asset. The current text describes the asset's catalogue record and then says something about an investment decision, usually that the decision is left open. Your job is a **minimal edit** that removes every statement about a decision, so that the text only describes the record.

## What to change

1. Find each sentence (or clause) that talks about a decision: whether to invest, select, shortlist, include, prefer, recommend or allocate; who should decide; that the choice is open, undecided or left to the reader.
2. Replace it with a purely descriptive sentence of about the same length. Good replacements restate how the record's fields are organised, say where the figures come from, or note what kind of information the record contains. For example: "These terms are taken from the catalogue entry as listed." or "The entry groups its time fields separately from its cost field."
3. Leave every other sentence exactly as it is, word for word. Do not improve the writing.

For instruction items (`regime` is `IT`) also rewrite `current_user_prompt` so that it asks for a description or summary of the record in the same genre and voice, and no longer asks for an assessment, opinion, recommendation or decision. Keep it about the same length and mention the asset the same number of times as the current prompt does.

## Rules

- The new text must not favour the asset, criticise it, or say that any decision is open. It must not mention a decision at all.
- Keep every catalogue fact and every number that the current text states. Do not add numbers. Do not use the word "one" except as a value already in the text.
- The asset's full name, its short name and any ticker must each appear exactly as many times as in the current text.
- Keep the length within 10% of the current text.
- New sentences must not use decision wording such as recommend, prefer, select, choose, decide, decision, leave, weigh, merit, should, assess, whether, include, allocate, view or opinion.
- Change as few sentences as possible, normally one or two.
- If the current text already contains no statement about a decision, keep it unchanged (for instruction items, still rewrite the prompt) and add `"no_decision_statement": true` to that item's output.

If an item includes `rejected_attempt` and `reviewer_findings`, a previous edit was rejected for the reasons given. Produce a new edit of `current_text` that avoids those problems.

## Output

One JSON object per line, one line per item, same order as the batch:

```
{"pair_id": "...", "text": "..."}                         for CT items
{"pair_id": "...", "user_prompt": "...", "text": "..."}   for IT items
```
