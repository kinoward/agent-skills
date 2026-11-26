# Agent Skills

A collection of AI agent skills for coding agents (Claude Code, Codex, Gemini CLI, Cursor, etc.).

## Skills

| Skill | Description |
|---|---|
| [mise-guide](./mise-guide/) | Teaches agents how to use [mise](https://mise.jdx.dev) — the polyglot dev environment manager |
| [git-commit-to-main](./git-commit-to-main/) | Local-only workflow: run project maintenance, split changes into Conventional Commits on a Conventional Branch, then fast-forward into `main` |
| [distill-session-history](./distill-session-history/) | Distill recurring problems and solutions from recent agent session history into durable project docs |
| [reconcile-project-docs](./reconcile-project-docs/) | Reconcile project documentation with the current conversation and repository state |
| [maintain-llms-txt](./maintain-llms-txt/) | Maintain and validate repository `llms.txt` navigation files |
| [maintain-release-version](./maintain-release-version/) | Maintain release versions and Keep a Changelog entries for single-version projects |
| [maintain-todo-md](./maintain-todo-md/) | Maintain and validate a repository `TODO.md` task list |

`git-commit-to-main` uses `maintain-llms-txt`, `maintain-todo-md`, and these skills from [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills): `make-repo-contribution`, `conventional-branch`, `commit-message-storyteller`, `conventional-commit`, `git-commit`.

## Install

Install any skill from this repo using [skills](https://github.com/vercel-labs/skills) CLI:

```bash
npx skills add https://github.com/kinoward/agent-skills
```

To install a specific skill:

```bash
npx skills add https://github.com/kinoward/agent-skills --skill mise-guide
```

## License

MIT
