# NSGI-ORS Pipeline

![Status](https://img.shields.io/badge/status-active-success)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)
![Topics](https://img.shields.io/badge/topic-federal_procurement-informational)

Non-Security General Intelligence Opportunity Registry (NSGI-ORS) pipeline.

Authoritative documents are version-controlled in `authoritative/`. Every removal or update must be traceable to a live SAM.gov extract and the verification pass.

## Contents

- `authoritative/NSGI_ORS_Master_Enumeration_2026-08-07.md`
- `authoritative/NSGI_ORS_Verification_Pass_2026-08-07.md`
- `authoritative/NSGI_ORS_Easy_Projects_Enumeration_2026-08-07.md`
- `authoritative/CDC_75D301-26-Q-79197_Draft_Contract_Package.md`

## Governance

- Branch strategy: `main` is authoritative production.
- Every change to `authoritative/` must go through PR review.
- Removal validation issues must include exact opportunity ID, SAM extract reference, verification pass reference, and dual confirmation.
- GitHub Actions workflow runs stale-listing detection and posts a review issue when inconsistencies are found.

## Verification

- Stale-listing workflow: `.github/workflows/stale-listing-detection.yml`
- Removal issue template: `.github/ISSUE_TEMPLATE/stale-listing-removal-validation.yml`
- PR checklist: `.github/PULL_REQUEST_TEMPLATE.md`

## License

MIT
