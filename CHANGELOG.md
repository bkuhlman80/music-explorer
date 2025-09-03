# Changelog

All notable changes will be documented here.

## [0.2.0](https://github.com/bkuhlman80/music-explorer/compare/music-explorer-v0.1.0...music-explorer-v0.2.0) (2025-09-03)


### Features

* **app:** env loader + marts-only guard; docs: PROVENANCE/README/CONTRIBUTING; ci: release-please; fix(make); tests: runtime guards ([1d8d792](https://github.com/bkuhlman80/music-explorer/commit/1d8d792d75140a30a7401bf0df42d772083bd969))


### Bug Fixes

* **ci:** use /bin/bash for make SHELL and call venv python directly ([a99cc82](https://github.com/bkuhlman80/music-explorer/commit/a99cc82db8a1ff63c882d6f73123b9536a9e40bd))
* POSIX activate and no double-quotes in pull ([8b492d5](https://github.com/bkuhlman80/music-explorer/commit/8b492d51d621859d13976ee23b1bfb0746ec6314))

## [Unreleased]
- Add live demo link once deployed
- Update PROVENANCE.md with latest pull dates

## [0.1.0] – 2025-09-03
### Added
- Core ETL pipeline raw→clean→marts
- Streamlit app (app/Main.py) with cached metrics
- Figures: collaboration network, genre evolution
- Report builder (docs/report.pdf)
- 17 passing tests (schema, transforms, viz sanity)
- CI workflow with lint + test + build
- Makefile hardened; pre-commit hooks

### Fixed
- Env quoting in CI
- SchemaResolver fallbacks for `artists` and `release_groups`
- SHELLFLAGS in Makefile

### Changed
- Tests relaxed to schema checks; optional REQUIRE_DATA=1
- Metrics panel with `use_container_width=True`
