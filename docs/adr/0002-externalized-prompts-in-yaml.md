# ADR 0002 — Externalized prompts in YAML

## Status

Accepted

## Context

Triage and response system prompts change more often than application code.
Hardcoding them in Python forces a deploy for every wording tweak.

## Decision

Store prompts under `src/hr_chatbot/llm/prompts/*.yaml` and load them via
`load_prompt(name)`. Nodes format `user_template` with runtime fields.

## Consequences

- Prompt diffs are reviewable without reading Python.
- Missing prompt files fail at first use with a clear error.
- Version control becomes the prompt registry (no separate CMS required).
