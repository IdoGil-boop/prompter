# Documentation Index

**Primary reference for agents**: use this file to find any project doc. When adding or renaming docs, update this index.

---

## Quick Start

1. **[README](../README.md)** — Project overview and setup

---

## Architecture

_Architecture and design docs go here as the project grows._

---

## Plans

- **[Implementation Plan](plans/2026-03-24-prompter-implementation-plan.md)** — Phased build plan: MVP prompt optimizer → tools → attribution → mock-first → escalation → polish
- **[Bloom Integrations Plan](plans/2026-03-25-bloom-integrations-plan.md)** — LLM-as-judge metric, test suite generation, behavioral guardrail

---

## Reference

- **[Common Gotchas](reference/COMMON_GOTCHAS.md)** — Known pitfalls and workarounds (cc10x build flow)
- **[Project Gotchas](gotchas.md)** — Counter-intuitive constructs found during debugging (`/bugfix` flow)
- **[Debug History](debug-history.md)** — Chronological log of bugs investigated and fixed

---

## Guides

_How-to guides (deployment, setup, onboarding) go here._

---

## Finding Documentation

- **Getting started?** → [Quick Start](#quick-start)
- **Understanding the system?** → [Architecture](#architecture)
- **Looking something up?** → [Reference](#reference)
- **What's the plan?** → [Plans](#plans)

---

### Guidelines

- Prefer **updating an existing doc** over creating a new one
- Create a **new file** only when the topic is distinct and needed for future work
- Name files by feature or topic, not by date or session
- Keep one doc per topic to prevent inflation
