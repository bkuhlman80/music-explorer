# Contributing Guide

This project uses **Conventional Commits** so that CI can automatically bump versions and update `CHANGELOG.md`.

## Commit message format

<type>(<scope>): <description>


- **type**: what kind of change
- **scope**: optional, part of codebase (e.g. `app`, `pipeline`, `ci`)
- **description**: short imperative summary

### Allowed types

- `feat`: new feature → bumps **minor** version
- `fix`: bug fix → bumps **patch** version
- `feat!` or body includes `BREAKING CHANGE:` → bumps **major** version
- `docs`: documentation only
- `chore`: build, tooling, deps, configs
- `refactor`: code restructure without new feature/fix
- `perf`: performance improvement
- `test`: adds or adjusts tests

### Examples

- feat(app): add artist decade filter
- fix(pipeline): handle missing release_group tags
- perf(collab): cache graph layout 
- docs(readme): add live demo link
- chore(ci): update Python matrix
- refactor(etl): split transforms into modules
- test(viz): tighten ±1% tolerance


### Rules of thumb
- Use present tense (“add”, not “added”).
- Keep under 72 chars if possible.
- Group related changes into one commit.
- Mention **BREAKING CHANGE:** in commit body if interface/contract changes.

## Workflow

1. Create a branch.
2. Make changes and commit using the format above.
3. Open a pull request.
4. Merge into `main`.  
   → CI + release-please will open/merge a release PR that bumps version and regenerates `CHANGELOG.md`.

---
