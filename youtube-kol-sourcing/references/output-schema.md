# Output schema

## Workbook sheets

Use these sheets unless the user requests another structure:

- `Screening Notes`
- `Small/Mid Creator Recommendations`
- `Headliner Benchmark Creators`
- `Active Review`
- `Watchlist`
- `Dedupe Audit` only when prior-list or competitor deduplication is used
- `Comment Review` only when comment review is attempted
- `Conditional Review Pool` only when the user authorizes fallback criteria

Only the two recommendation sheets are strict final pools. Do not create a generic rejected-candidate dump by default.

## Required columns

Keep the first ten columns in this exact order; `Owner` may be blank but must remain:

1. Creator Name
2. Avatar
3. Creator Link
4. Subscribers
5. Owner
6. Platform
7. Email
8. Country
9. Notes
10. Rating
11. Email Source / Verification Method
12. Contact Status
13. YouTube Email Button
14. Backup Contact Route
15. Contact Verification Date
16. Creator Size
17. Language
18. Main Content Direction
19. Account Age / Earliest Visible Upload
20. Recent 10 Content Observation
21. Recent 10 View Details
22. Recent 10 Average Views
23. Recent 6 Average Views
24. Recent 6 Median Views
25. Latest Relevant Upload Date
26. Face / Human Persona
27. Human Explanation / Voiceover
28. Product Demo Ability
29. Content Quality Score
30. Audience Type
31. Audience Fit Score
32. Why This Creator Fits
33. Best Partnership Angle
34. Why This Angle Fits This Creator
35. Suggested Collaboration Format
36. Suggested Budget Range
37. Business Contact Route
38. Recent Sponsored Content
39. Risk Notes
40. Outreach Angle
41. Dedupe Status
42. Competitor / Exclusion Check
43. Source / Verification Date

## Conditional columns

When fallback criteria are used, add `Acceptance Condition`, `Condition Evidence`, and `Final Review Note` after `Rating`. Name the exact exception and measured evidence, then state whether the row is suitable for priority outreach, a low-budget test, manual format review, or another bounded use.

## Comment-review columns

When comments are reviewed, append: videos sampled, sample size, capture status, audience profile, high-value-comment ratio, buyer-question signals, relevant problem or use-case comments, spam risk, comment-quality score, and whether comments support collaboration.

## Rating guidance

- `A-Priority`: strong fit, contact route, recency, and playback.
- `B+Test`: passes strict gates with a bounded risk.
- `Watchlist`: promising but missing a final-gate requirement.
- `Conditional Test`: meets user-defined fallback criteria but is not strict.

Ratings never override hard gates.

## Screening notes

Keep this sheet operational: task scope and target count, strict and conditional gates, dedupe sources and freshness, market and competitor exclusions, contact definition, comment-review status, and any shortfall explanation.

