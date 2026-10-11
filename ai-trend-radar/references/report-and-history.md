# Report and history

## Compact default

Write in the requested language, defaulting to Simplified Chinese. The labels below describe the structure; translate them naturally in the delivered report.

Open with 2–3 sentences containing the inspected distinct-event count, the time window and timezone, and the strongest supported themes. If coverage is limited, identify the material gap briefly. Never reuse an illustrative count as a result.

For each ranked event:

```text
## 1. A natural title that explains the interesting change

[What happened, including the few numbers that matter. What became new today.]

Judgment: [A concrete interpretation, practical consequence, or useful open question.]

Signal: [3/5, 4/5, or 5/5 stars] · Status: [supported information status]
Time: [original publication time; event time if different; new development time if applicable]
Sources: [direct original source link first; independent test or reporting as needed]
```

Use two short paragraphs rather than a separate heading for every field. Keep the judgment distinct from factual reporting. Prefer direct, conversational language with a reason to care. Do not imply firsthand testing when only a demo, paper, or someone else's test was inspected.

State that fewer than 10 events qualified when that is the result; keep the explanation short. If nothing qualifies, report that outcome and omit empty rankings or invented priority reads.

## Detailed mode

When requested, expand each item into separate sections for what happened, why it matters today, judgment, signal strength, information status, time, and original sources. Preserve the same evidence standards; detailed mode changes presentation, not the search target or confidence.

## Closing sections

1. **Still developing** (optional): at most 1–3 distinct older stories with a substantive update in the run window, within the default 48-hour lookback unless the user chose another period. Give the original date and the actual reason they resurfaced. Do not duplicate the main list.
2. **Today's AI trend signals:** normally 2–4 patterns, each in 1–2 sentences, but only as many as evidence supports. Connect at least two independent listed events per pattern. A lack of qualifying patterns is an acceptable result. Claims that a formerly hot topic has gone quiet must be limited to the inspected scope.
3. **If you only read four:** choose up to four of the listed events with one reason each. If fewer exist, choose fewer and adjust the heading.
4. **If you only read one:** identify the highest-value event and explain the choice in a sentence. Omit when no event qualifies.

## History and saved reports

Use prior reports supplied in the conversation or an explicitly available report/history location. Do not search unrelated private directories for hidden history. If history is absent, deduplicate the current pool and briefly state that earlier-run duplication could not be checked.

When the user requests saved reports, use their chosen destination. If a writable project is available and no location was specified, use `reports/ai-trend-radar/`. Save a Markdown report with a dated filename; include a time suffix if that date already exists. Keep run artifacts out of the installed skill folder.

Alongside saved reports, maintain `history.jsonl` with one object per included event:

| Field | Meaning |
|---|---|
| `event_key` | Stable underlying-event identity, such as organization + product/project + release/version/topic. Reuse it for follow-ups to that event. |
| `title` | Title as included in the report. |
| `original_published_at` | Original source timestamp with timezone, or null if unknown. Preserve the source's actual precision. |
| `last_included_at` | Run timestamp with timezone. |
| `new_development` | Specific change justifying this inclusion; identify first inclusion when applicable. |
| `source_urls` | Direct supporting links inspected for this inclusion. |
| `report_file` | Relative path of the saved report. |

Read existing history before selecting repeat events. Match by underlying identity and canonical source, not title wording alone; different reports may describe the same event differently. Preserve first-publication time on later inclusions. Append after saving the report, preserve existing records, and avoid duplicating the same event/report pair when retrying a save.

Write history only for a requested saved report or when the user explicitly requested persistence. If files cannot be saved, deliver the report in chat and identify that persistence was unavailable. A successful report does not imply persistent memory or a background monitor.
