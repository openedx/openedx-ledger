# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Before opening a PR or pushing a branch

Run a self-check on the diff before creating a PR or pushing:
1. Compute effective LoC — exclude lockfiles, generated files, snapshots, and vendor code.
2. Count effective touched files — exclude the above plus one-to-one test pairs.
3. If effective LoC > 400 or effective files > 10, stop and propose a split before proceeding.
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
