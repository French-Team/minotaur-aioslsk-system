# Project knowledge

This file gives Freebuff context about your project: goals, commands, conventions, and gotchas.

## What this is
A collection of **custom AI agents** for use with [Codebuff](https://codebuff.com) — a CLI tool where you chat with AI to code. Agents are TypeScript files that define specialized AI behaviors using the `AgentDefinition` interface.

## Quickstart
- **Setup:** Run `codebuff` from project root. Agents live in `.agents/`.
- **Test / run:** `codebuff` loads agents from `.agents/` automatically. Invoke agents via `@AgentName` in chat.
- **Publish:** `codebuff publish your-agent-name` (requires Codebuff CLI).

## Key directories
| Path | Purpose |
|------|---------|
| `.agents/` | Agent definitions loaded by Codebuff |
| `.agents/types/` | TypeScript types (`AgentDefinition`, input/output schemas, tool types) |
| `codebuff-dot-agents/` | Original agent examples, skills, and templates (not loaded by Codebuff) |
| `codebuff-dot-agents/examples/` | Example agents: diff-reviewer, git-committer, file-explorer |
| `codebuff-dot-agents/skills/` | Reusable skill definitions (each subdirectory has a `SKILL.md` with YAML frontmatter) |

## Custom agents (in `.agents/`)

### Multi-agent system for aioslsk (Soulseek Python library)
These three agents work together as a team. The interface builder and backend developer **must** spawn the researcher before using any aioslsk APIs — they are strictly forbidden from inventing API signatures.

| Agent | File | Purpose |
|-------|------|---------|
| **researcher-aioslsk** | `.agents/researcher-aioslsk.ts` | Researches aioslsk docs at https://aioslsk.readthedocs.io/en/stable/ — the **single source of truth** for API signatures |
| **aioslsk-interface-builder** | `.agents/aioslsk-interface-builder.ts` | Builds FastAPI web interfaces using verified aioslsk APIs (spawns researcher) |
| **backend-aioslsk** | `.agents/backend-aioslsk.ts` | Implements backend business logic using verified aioslsk APIs (spawns researcher) |

### Other agents
- **`codebuff-dot-agents/my-custom-agent.ts`** — Starter custom agent (uses `x-ai/grok-4-fast` model)

## Architecture
- Each agent is a standalone `.ts` file exporting an `AgentDefinition` object
- Agents define: `id`, `displayName`, `model` (OpenRouter models), `toolNames`, `instructionsPrompt`, and optional `handleSteps` generator for programmatic logic
- Agents can spawn sub-agents using the `spawn_agents` tool
- Skills provide reusable behaviors loaded via the `skill` tool
- Supported models include Claude, GPT, Grok, Gemini, DeepSeek, Llama, and more (via OpenRouter)

## Conventions
- **License:** Apache 2.0
- **Language:** TypeScript
- **Agent IDs:** kebab-case (e.g., `basic-diff-reviewer`)
- **Skills:** Each skill lives in its own directory with a `SKILL.md` containing YAML frontmatter (`name`, `description`, `license`) followed by instructions
- **Skill loading:** Project-level skills are in `.agents/skills/`, global ones in `~/.agents/skills/`; project takes precedence
- **Testing:** No dedicated test framework — agents are tested by running `codebuff` and invoking them interactively

## Things to avoid
- Don't use deprecated model names — check `types/agent-definition.ts` for the current model enum
- Skill names must be lowercase alphanumeric with hyphens (1–64 chars), match their directory name, no consecutive hyphens
