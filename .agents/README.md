# Agent Entry Point

> READ THIS FIRST BEFORE DOING ANY WORK IN THIS REPOSITORY.

The canonical execution plan is:

`.agents/MASTER_PLAN.md`

Every coding agent, CLI agent, IDE agent, or human-assisted agent working on this repository must read that file before proposing, editing, refactoring, collecting data, changing architecture, or creating new branches.

## Working rules

1. `main` is the canonical working branch.
2. The goal is one master website with five tabs: Home, VtuberRecord, SNA, Data Analytics Dashboard, and Financial Data Analytics Dashboard.
3. Google Sheet is the master editable registry/data source. Exported JSON is a derived website artifact, not a competing source of truth.
4. Reuse existing ThaiVtuberSNA and ThaiVirtualCreatorRegistry code/data before writing replacements.
5. Do not create new repos, long-lived branches, parallel frameworks, duplicate frontends, duplicate pipelines, or extra architecture unless the user explicitly asks.
6. Do not add data-validation suites, audit projects, synthetic-data campaigns, benchmarking projects, or regression campaigns that delay the requested website.
7. Do not reintroduce the old 1,370-channel ceiling or 100-subscriber admission gate.
8. New public interaction data may store public platform account IDs/display names directly; do not require HMAC for newly collected public actor identities.
9. Existing HMAC-only history must not be claimed to be reversible without an actual mapping/key.
10. Progress is measured by questions the website can answer, not by file count, test count, documents, abstractions, or infrastructure.
11. Execute the seven phases in `.agents/MASTER_PLAN.md` in order unless the user explicitly changes priorities.
12. At each milestone report only: what changed, where to see it, the commit, and what real data/functionality is still missing.

If another document conflicts with `.agents/MASTER_PLAN.md` on project direction, treat `.agents/MASTER_PLAN.md` as the current project direction unless the user gives a newer explicit instruction.
