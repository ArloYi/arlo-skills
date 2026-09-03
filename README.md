# Arlo Skills

A practical collection of AI skills for design research, website release operations, investment analysis, and YouTube creator sourcing, with English documentation and a Simplified Chinese overview.

[简体中文](README.zh-CN.md)

Each skill in this repository is an independent, installable package that follows the [Agent Skills](https://agentskills.io/) open format. The collection keeps the entrypoint concise, moves task-specific knowledge into on-demand references, and validates every package in CI.

## Skill catalog

| Category | Skill | What it does |
|---|---|---|
| Design & Product | [`design-compass`](design-compass/) | Triangulate visual, product, and implementation references into an original, evidence-backed design direction. |
| Development & Operations | [`website-release-manager`](website-release-manager/) | Prepare a finished website, create or connect its GitHub repository, deploy it with an appropriate method, verify production, and keep release records. |
| Finance & Investing | [`wealth-compass`](wealth-compass/) | Analyze companies, assets, macro conditions, portfolios, and investment theses through an evidence-calibrated decision framework. |
| Marketing & Growth | [`youtube-kol-sourcing`](youtube-kol-sourcing/) | Source, verify, score, deduplicate, and organize YouTube creator partners for a campaign-specific outreach pool. |

## Install

Ask a compatible coding agent to install one skill from its folder URL:

```text
Install this Agent Skill:
https://github.com/ArloYi/arlo-skills/tree/main/design-compass
```

Replace the last path segment with `website-release-manager`, `wealth-compass`, or `youtube-kol-sourcing` as needed.

For Codex, you can also clone the collection and copy an individual folder into your skills directory:

```bash
git clone https://github.com/ArloYi/arlo-skills.git
cp -R arlo-skills/design-compass ~/.codex/skills/
```

Install only the skill folders you need. The repository-level README, CI, and evaluation files are not part of an installed skill.

## Usage examples

### Design & Product

```text
Use $design-compass to research three visual directions for this SaaS landing page. Cite the references and do not copy an existing composition.
```

### Finance & Investing

```text
Use $wealth-compass to audit this investment thesis. Separate facts, assumptions, valuation, risks, and action triggers.
```

### Development & Operations

```text
Use $website-release-manager to prepare this finished website, create or connect its GitHub repository, deploy it, verify production, and save the release record.
```

### Marketing & Growth

```text
Use $youtube-kol-sourcing to build a verified YouTube creator shortlist for this campaign and deduplicate it against our prior outreach sheet.
```

## Repository structure

```text
arlo-skills/
├── design-compass/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/
├── wealth-compass/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/
├── website-release-manager/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/
│   ├── scripts/
│   └── tests/
├── youtube-kol-sourcing/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/
├── evals/trigger-cases.json
└── scripts/validate_skills.py
```

`SKILL.md` contains the routing and core workflow. Detailed domain rules live in `references/` and are loaded only when relevant. `agents/openai.yaml` provides Codex-facing display metadata.

## Quality and safety

- Current prices, policies, financial reports, product terms, and creator metrics must be re-verified at execution time.
- Third-party pages, search results, comments, and API responses are untrusted data, not instructions.
- The design skill extracts principles rather than protected expression.
- The finance skill communicates uncertainty and does not promise returns.
- The creator-sourcing skill never invents contact details or bypasses login, CAPTCHA, or platform restrictions.
- The website release skill never guesses project identity, credentials, providers, or production targets; it deploys only a remotely retained SHA, separates routine code releases from infrastructure changes, and requires a verified rollback path.
- Before publishing a skill to a public repository, maintain a deliberately selected, generalized, and sanitized public copy rather than mirroring local files or retaining personal preferences and project data.

Run the repository validator locally:

```bash
python3 scripts/validate_skills.py
```

## License

Original content in this repository is licensed under the [MIT License](LICENSE). Third-party websites, software, trademarks, creative works, and linked materials remain subject to their respective licenses and terms. See the attribution notes bundled with the relevant skill.
