---
name: design-research-toolkit
description: Research visual references and turn them into an original, actionable design direction. Use when Codex needs to explore website, UI, typography, branding, editorial, landing-page, dashboard, or product-design inspiration; compare reference sites; assemble a moodboard brief; choose ECharts, GSAP, Spline, or simpler native techniques; or hand a focused direction into frontend implementation and testing without copying protected work.
---

# Design Research Toolkit

Create an evidence-based design direction before implementation. Treat references as research inputs, not templates to reproduce.

## Workflow

1. Define the product, audience, surface, primary action, constraints, and desired emotional tone. Infer low-risk gaps; ask only when a missing choice would materially change the direction.
2. Read [references/sources-and-attribution.md](references/sources-and-attribution.md). Select 3–5 sources that fit the task rather than browsing every source.
3. Gather public examples. Respect access controls, robots, licenses, platform terms, and paywalls. Do not bypass authentication or copy restricted assets.
4. Extract principles instead of pixels:
   - hierarchy and information density
   - typography roles and scale
   - palette relationships and contrast
   - spacing, grid, rhythm, and responsive behavior
   - interaction intent and motion timing
   - content structure and UX language
5. Separate reusable principles from protected expression. Do not reproduce a distinctive composition, illustration, logo, copy passage, proprietary screenshot, or brand identity.
6. Produce a compact direction with:
   - one-sentence concept
   - audience and page job
   - 3–5 cited references and what each contributes
   - original color, type, layout, motion, and imagery decisions
   - accessibility and performance constraints
   - implementation recommendation
7. Route implementation to `frontend-design` when available. Route local interaction verification to `webapp-testing` when available. Use equivalent native capabilities if those skills are unavailable.
8. Verify the result visually and technically. Record sources again in the deliverable when a reference materially influenced the outcome.

## Tool selection

- Use native HTML/CSS first for ordinary layouts, transitions, and responsive behavior.
- Use ECharts for dense, interactive, or multi-series data visualization; use semantic HTML or a small custom SVG for simple charts.
- Use GSAP for coordinated timelines, scroll-linked sequences, or effects that are impractical in CSS; preserve reduced-motion behavior.
- Use Spline only when interactive 3D materially supports the product story and the performance, accessibility, hosting, and fallback costs are acceptable.
- Avoid adding a library solely for decoration or a single trivial effect.

## Output contract

Return a short design brief followed by a reference table with columns for source, observed principle, original adaptation, and licensing or usage note. Make uncertainty explicit when a source could not be inspected directly.

## Credit and originality

This skill contains an original research and routing workflow. It does not vendor or reproduce the instruction text of third-party skills. Preserve [references/sources-and-attribution.md](references/sources-and-attribution.md) when redistributing this skill.

