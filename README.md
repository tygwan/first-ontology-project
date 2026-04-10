# Data Storage Policy

## Purpose

This directory stores versioned data snapshots used for semantic modeling, testing, and connector validation.

## Rules

- Do not keep raw data files at the repository root.
- Keep only a small number of curated baseline snapshots in Git.
- Use dated folders for immutable source snapshots.
- Keep generated scratch outputs, temporary files, and local experiments out of Git.

## Current Layout

- `raw/dxtnavis/2026-03-23`
  - `AllProperties_20260323_063038.csv`
  - `pipeline_schedule_20260323_063138.csv`
  - `Refining_ObjectID_20260323_063058.xlsx`

## Storage Strategy

### Track in Git

Track a baseline data set in Git when:

- it is needed to reproduce semantic mapping or integration tests
- its size remains manageable for the repository
- it represents a stable reference snapshot

### Do not track in Git

Do not track data in Git when:

- repeated exports create many large snapshots
- the files are temporary or exploratory
- the data is sensitive or environment-specific

## Future Policy

- Keep one or a few canonical baseline snapshots under `data/raw`.
- If snapshot size or count grows materially, move large data handling to `Git LFS` or external storage and keep only manifests in the repository.
