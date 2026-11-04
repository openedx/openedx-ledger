# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Before opening a PR or pushing a branch

Run a self-check on the diff before creating a PR or pushing:
1. Confirm the diff is one coherent change — a single purpose a reviewer can hold in their head.
2. Look for logical seams: independently shippable or reviewable concerns bundled together (a refactor mixed with a feature, unrelated fixes, a schema migration plus unrelated UI work). If you find them, stop and propose a split along those seams before proceeding.
3. Size alone is never a reason to split. Note effective LoC and touched files (excluding lockfiles, generated files, snapshots, vendor code, and one-to-one test pairs) so reviewers can plan time; for a large but cohesive diff, suggest a review order or commit-by-commit reading.
4. Report the result inline before continuing.

## Key Principles

- Search the codebase before assuming something isn't implemented
- Write comprehensive tests with clear documentation
- Follow Test-Driven Development when refactoring or modifying existing functionality
- Always write tests for new functionality you implement
- Keep changes focused and minimal
- Follow existing code patterns
- Prefer the `ddt` package for parameterized tests to reduce code duplication

## Documentation & Institutional Memory

- Document new functionality in `docs/references/`
- When you learn something important about how this codebase works (gotchas, non-obvious
  patterns, integration quirks), capture it in the relevant `docs/references/` file or
  in `docs/architecture-patterns.md`
- These docs are institutional memory - future sessions (yours or others) will benefit
  from what you record here

## Testing Notes

- Uses pytest with Django integration
- Coverage reporting enabled by default
- PII annotation checks required for Django models
