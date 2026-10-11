# AI Trend Radar

Find the AI developments worth your attention, with original sources and a reason to care.

AI Trend Radar is an Agent Skill for a selective briefing on recent global AI changes. It searches across official releases, developer communities, research, independent tests, and reliable reporting, then explains what changed and why it matters now.

The skill instructions, reference files, and UI metadata are in English. Reports default to Simplified Chinese; request English or another language when invoking it.

## What it does

- Prioritizes models, core products, agents, coding tools, research, and practical creative workflows.
- Aims to inspect 40–80 distinct events for a broad daily scan and selects up to 10, without filling quiet days with weak updates.
- Distinguishes launch dates, actual event dates, new evidence, availability, vendor measurements, and unconfirmed reporting.
- Merges repeated coverage and checks earlier reports when history is available.
- Identifies trends supported by independent events, then highlights up to four priority reads and one highest-value read.
- Offers compact and detailed reports, with optional saved reports and a local event history.

## Install

Install the skill from the repository's `main` branch.

Ask Codex to install:

```text
Use $skill-installer to install ai-trend-radar from ArloYi/arlo-skills, ref main, path ai-trend-radar.
```

Or copy the skill folder from the published branch:

```bash
git clone --branch main --single-branch https://github.com/ArloYi/arlo-skills.git
mkdir -p ~/.codex/skills
cp -R arlo-skills/ai-trend-radar ~/.codex/skills/
```

The copy example assumes a fresh checkout and no existing installation of this skill. Preserve any existing installation before replacing it. Install only `ai-trend-radar/`; the collection's other files are not required.

## Use

Daily briefing:

```text
Use $ai-trend-radar to scan today's global AI developments.
```

Focused briefing:

```text
Use $ai-trend-radar to review the last 24 hours of AI coding and agent developments. Return at most five items in English.
```

Saved report with cross-run checks:

```text
Use $ai-trend-radar for today's AI briefing. Save the report and event history in reports/ai-trend-radar/ and check that history for repeated stories.
```

Detailed report:

```text
Use $ai-trend-radar to produce a detailed AI briefing for the last 20 hours. Separate facts, judgment, status, time, and sources for each event.
```

The user's period, topic, language, and item limit override the defaults.

## Defaults and prerequisites

| Setting | Behavior |
|---|---|
| Time window | Prioritize 12 hours; widen to 20; inspect older stories within 48 hours only when a substantive update occurred in the run window. |
| Output | Up to 10 qualifying events, compact format, Simplified Chinese. |
| Sources | Prefer original official evidence and non-Chinese-language sources; source preference can be overridden. |
| Live information | Requires a host agent with live search and source retrieval. The skill does not bundle a news API or bypass source access restrictions. |
| Repetition checks | Uses supplied previous reports or an accessible history location. Without those, checks are limited to the current run. |
| Saved history | Created alongside reports when saving or persistence is requested; not stored inside the installed skill. |
| Scheduling | Requires separate automation configuration. Installing or invoking this skill does not schedule a daily run. |

Search coverage depends on available tools, accessible sources, and the requested scope. Counts reflect actual inspected events, not a guarantee of full-web coverage. The included trigger cases and package validators check routing examples and structure; they are not evidence of a completed live news scan.

## Package

`SKILL.md` defines the workflow. `agents/openai.yaml` supplies Codex UI metadata. Three references cover source discovery, selection and evidence, and report/history conventions.

Original instructions are licensed under the repository's [MIT License](https://github.com/ArloYi/arlo-skills/blob/main/LICENSE). Source names, trademarks, linked publications, and third-party material retain their respective ownership and terms.
