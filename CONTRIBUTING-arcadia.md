# Contributing to the Arcadia LiteLLM fork (SRE change control)

This file is Arcadia-specific and does not replace the upstream [`CONTRIBUTING.md`](CONTRIBUTING.md). It documents the change-control rules that apply to this fork because it feeds Arcadia's ARIA and AI infrastructure. Follow both: upstream contribution mechanics from `CONTRIBUTING.md`, plus the SRE/HITRUST rules below.

Canonical spec: [SRE / HITRUST Change Control for ARIA & AI Infrastructure](https://arcadia-io.atlassian.net/wiki/spaces/AIFM/pages/1830977769)

## Change Control & SRE Rules

### What this repo is (env class)

This repository is the SRE-owned LiteLLM fork. It is **solution-level code** that feeds **both** the `dev-ai` (ai-development-arcadia-io) and `prd-ai` (aria-arcadia-io) gateways. Per the change-control decision matrix, the fork's env class is **AIFM only (no ACM)**. SRE owns the fork and reviews or is notified on rollout. An SRE ticket is required only when a change is platform-wide (affects the CCT chart / all consumers).

The config that the fork is deployed with carries its own requirements, and those are stricter than the fork code itself:

- **dev-ai config** (dev-ai / ai-development-arcadia-io): AIFM only, no ACM. `dev-ai` was scoped out of ACM entirely.
- **prd-ai config** (prd-ai / aria-arcadia-io): AIFM plus a paired ACM Specialty Change Request (SCR), approved **before promotion** by an approver group (not the reporter). SRE reviews or is notified.
- **platform-infra** (CCT chart / all consumers): AIFM plus an SRE ticket (plus an ACM SCR if it is a prod cutover); SRE review is mandatory and gating.

### Required ticket linkage

Every change references an **AIFM-#### ticket** in the branch work, the commit body, and the PR title or body. The `change-control-guard.yml` workflow fails any PR into `litellm_internal_staging` (or `main`) that lacks an `AIFM-####` or `ACM-####` reference. When the change promotes config to `prd-ai`, also reference the **ACM SCR** (`ACM-####`), approved before promotion.

### Branch and review rules

- Never commit directly to `main`. Branch off `litellm_internal_staging` (the integration branch). The `guard-main-branch.yml` gate only admits `litellm_internal_staging` or `litellm_hotfix_*` sources into `main`.
- Branch names are prefixed `litellm_` and contain no slashes (commitlint enforces this on the team's repos).
- Peer review before merge: the approver must not be the implementer.
- SRE is a required reviewer on prod-sensitive paths (see [`.github/CODEOWNERS`](.github/CODEOWNERS)): the proxy gateway, enterprise code, and deploy assets. `@arcadia/sre` is the owning team.

### Non-negotiables

- No direct commits to `main`.
- Peer review before merge (approver != implementer).
- Tracked ticket linkage: AIFM always; an ACM SCR at `prd-ai` promotion.
- A rollback plan written down before implementation.
- Tested in `dev-ai` before `prd-ai`.
- Timestamped audit-evidence screenshots captured for the change record.

### Tracking

Work governed by this policy references **AIFM-847** (the change-control rollout ticket) until superseded.
