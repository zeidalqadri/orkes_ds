# ADR 001: Pipeline Status Model

**Date**: 2026-04-28  
**Status**: Accepted

## Context
The alumni discovery pipeline uses a `discovery_status` column to track each profile's progress through: PENDING → PROCESSING → DISCOVERED → REVIEW → HIGH.

## Decision
Use a single status column with an ordered lifecycle. Each transition is forward-only. The model encodes confidence implicitly:
- PENDING = not yet started
- PROCESSING = currently being harvested/enriched
- DISCOVERED = raw data collected, needs review
- REVIEW = flagged for LLM verification
- HIGH = verified, high confidence

## Consequences
- Simple to implement and query
- Status transitions are unambiguous
- No branching states — strict linear progression
- Can't express "verified but low confidence" without adding new states
