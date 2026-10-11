---
name: design-compass
description: Research and triangulate visual references into an original, evidence-backed design direction before implementation. Use for website or product UI inspiration, reference comparison, moodboards, interaction and component research, redesigns, and design-tooling choices.
---

# Design Compass

Turn references into a focused design direction that can be defended and built. Treat every source as evidence for a specific decision, never as a template to reproduce.

## Workflow

1. Frame the brief: product, audience, surface, primary task, required content and states, constraints, and emotional tone. Inspect an existing interface before researching its replacement. Infer low-risk gaps; ask only when an answer would materially change the direction.
2. Read [references/sources-and-attribution.md](references/sources-and-attribution.md), then select 3–5 sources by evidence role. For functional product UI, include at least one live product or real-flow archive. For culturally specific work, include a relevant regional source.
3. Inspect the strongest source pages directly when access allows. Record the canonical URL, what was actually observed, and any login, paywall, stale-page, or rendering limitation. Treat search results and aggregators as discovery paths until the original page is inspected.
4. Separate the evidence:
   - **Product evidence:** tasks, flows, states, content, and responsive behavior from shipped interfaces.
   - **Composition evidence:** hierarchy, density, grid, spacing, typography, palette, and imagery.
   - **Craft evidence:** transitions, micro-interactions, motion timing, and expressive details.
   - **Implementation evidence:** component behavior, accessibility semantics, dependencies, performance, and license.
5. Triangulate instead of averaging. Identify recurring principles, useful tensions, and task-specific outliers. Use concept galleries for visual exploration, not as proof of usability; use component demos as implementation candidates, not as a product strategy.
6. Form an original direction: one concept, explicit design decisions, what to avoid, and why the direction fits the audience and page job. Separate reusable principles from protected expression; preserve the source's distinctive composition, illustration, logo, copy, assets, and brand identity as reference-only material.
7. If implementation is requested, route the direction into an available frontend or UI implementation skill and choose the smallest suitable technique. If the request is research-only, stop with the brief.
8. Verify the deliverable. Reopen material links, mark uncertainty, check accessibility and performance constraints, and visually inspect any implementation at representative viewports.

## Implementation choices

- Prefer semantic HTML and native CSS for ordinary layouts, transitions, and responsive behavior.
- Use a small custom SVG for simple charts; use ECharts for dense, interactive, or multi-series data visualization.
- Use GSAP for coordinated timelines or scroll-linked sequences that would be impractical in CSS, with a reduced-motion path.
- Use Spline only when interactive 3D supports the product story and its performance, accessibility, hosting, and fallback costs are acceptable.
- Treat React Bits, Aceternity UI, Uiverse, Origin UI, and similar collections as optional implementation references. Inspect the exact component, dependencies, accessibility, and current license before adapting code.

## Completion criteria

A direction is complete only when:

- 3–5 relevant sources were selected and the strongest pages were inspected directly when possible;
- every cited source has an observed contribution rather than a generic style label;
- functional recommendations are grounded in product or behavior evidence, not concept imagery alone;
- each proposed decision states an original adaptation and a reason tied to the brief;
- access limits, uncertain claims, licensing constraints, and implementation tradeoffs are visible.

## Output contract

Return a compact design brief followed by a reference table with columns for source, evidence role, observed principle, original adaptation, and access or usage note. When implementation is requested, add a short build recommendation and verification checklist.

## Credit and originality

This skill contains an original research and routing workflow. It does not vendor third-party source material or instruction text. Preserve [references/sources-and-attribution.md](references/sources-and-attribution.md) when redistributing the skill.
