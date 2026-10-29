# Engineering Change Management SOP (ENG-SOP-09)

Effective: 2025-02-01 | Owner: Platform Engineering

## Change classes

- **Standard**: Pre-approved low-risk changes (library bumps, docs). Peer review only.
- **Normal**: Feature releases and config changes. Require PR review + CI green + change ticket.
- **Emergency**: Production-down or security hotfix. May bypass full CAB with post-facto review within **24 hours**.

## Deployment windows

Normal production deploys occur **Tue–Thu, 10:00–16:00 UTC**. Freezes apply during company-wide events listed in the freeze calendar.

## Rollback

Every normal change must document a rollback plan. If error rate exceeds **2x baseline** for 10 minutes post-deploy, the on-call engineer executes rollback and opens a SEV-2 if customer impact is confirmed.

## CAB

The Change Advisory Board meets Mondays. Changes affecting shared multi-tenant infrastructure need CAB approval unless classified emergency.
