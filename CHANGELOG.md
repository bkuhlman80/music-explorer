# Changelog

All notable changes will be documented here.

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
