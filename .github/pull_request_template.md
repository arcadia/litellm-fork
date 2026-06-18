## Relevant issues

<!-- e.g. "Fixes #000" -->

## Linear ticket

<!-- if you are an internal contributor, add the Linear ticket e.g. "Resolves LIT-1234" to magically link the Linear ticket to the GitHub PR -->

## Pre-Submission checklist

**Please complete all items before asking a LiteLLM maintainer to review your PR**

- [ ] I have Added testing in the [`tests/test_litellm/`](https://github.com/BerriAI/litellm/tree/main/tests/test_litellm) directory, **Adding at least 1 test is a hard requirement** - [see details](https://docs.litellm.ai/docs/extras/contributing_code)
- [ ] My PR passes all unit tests on [`make test-unit`](https://docs.litellm.ai/docs/extras/contributing_code)
- [ ] My PR's scope is as isolated as possible, it only solves 1 specific problem
- [ ] I have requested a Greptile review by commenting `@greptileai` and received a **Confidence Score of at least 4/5** before requesting a maintainer review

## Delays in PR merge?

If you're seeing a delay in your PR being merged, ping the LiteLLM Team on [Slack (#pr-review)](https://join.slack.com/t/litellmossslack/shared_invite/zt-3o7nkuyfr-p_kbNJj8taRfXGgQI1~YyA).

## CI (LiteLLM team)

> **CI status guideline:**
>
> - 50-55 passing tests: main is stable with minor issues.
> - 45-49 passing tests: acceptable but needs attention
> - <= 40 passing tests: unstable; be careful with your merges and assess the risk.

- [ ] **Branch creation CI run**  
       Link:

- [ ] **CI run for the last commit**  
       Link:

- [ ] **Merge / cherry-pick CI run**  
       Links:

## Screenshots / Proof of Fix

<!-- Include screenshots, screen recordings, or log output demonstrating that your changes work as expected.
     For bug fixes: show reproduction before the fix and passing behavior after.
     For new features: show the feature working end-to-end.
     For UI changes: include before/after screenshots. -->

## Type

<!-- Select the type of Pull Request -->
<!-- Keep only the necessary ones -->

🆕 New Feature
🐛 Bug Fix
🧹 Refactoring
📖 Documentation
🚄 Infrastructure
✅ Test

## Changes

<!-- Describe what changed. -->

---

## Arcadia change control (SRE / HITRUST)

<!-- Required for this SRE-owned fork. Spec: https://arcadia-io.atlassian.net/wiki/spaces/AIFM/pages/1830977769 -->
<!-- See CONTRIBUTING-arcadia.md for the env class and rules. -->

**AIFM ticket:** <!-- AIFM-#### (required for every change) -->

**ACM SCR:** <!-- ACM-#### required for prd-ai (aria-arcadia-io) promotions; write N/A otherwise -->

**Environment touched** (select one):

- [ ] solution-code (the fork itself; AIFM only, no ACM)
- [ ] dev-ai (ai-development-arcadia-io; AIFM only, no ACM)
- [ ] prd-ai (aria-arcadia-io; AIFM + approved ACM SCR before promotion)

**Attestations:**

- [ ] This PR is from a `litellm_` branch off `litellm_internal_staging`, not from `main`
- [ ] The approver is not the implementer (peer review before merge)
- [ ] A rollback plan exists and is written down before implementation
- [ ] SRE has reviewed or been notified (required on proxy, enterprise, and deploy paths via CODEOWNERS)
- [ ] Tested in `dev-ai` before any `prd-ai` promotion
- [ ] Timestamped audit-evidence screenshots are attached or linked
