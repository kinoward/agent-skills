# Community Sources

This skill follows community patterns but keeps them scoped to the target repository's local rules and this skill's default policy.

## Adopted

- AnswerDotAI `llms.txt`: use Markdown with H1, blockquote summary, optional details, and H2 file-list sections. Treat `Optional` as a special skip-able section, not a normal heading.
- GitHub `awesome-copilot` `create-llms` and `update-llms`: analyze repository purpose, prioritize essential files, write concise link descriptions, and validate relative links. Use their create/update split as workflow inspiration, not their root-only file scope.
- Microsoft `wiki-llms-txt`: borrow the idea of clearly separating discovery files from full expanded context, while keeping directory-level navigation as this skill's default policy.
- Vercel `geistdocs`: treat its `/llms.txt` support as a documentation-site pattern, not as repository maintenance policy.
- Agent Skills conventions: keep `SKILL.md` concise, place reusable checks in `scripts/`, detailed policy in `references/`, and copyable shapes in `assets/`.

## Not Adopted

- Do not generate `llms-full.txt` or expanded context files by default.
- Do not crawl external URLs from validation scripts.
- Do not include generated output, dependencies, build artifacts, or cache directories.
- Do not replace a target repository's local coverage model with a single root `llms.txt` unless local rules explicitly require it.
- Do not create directory-level `llms.txt` files under `.agents`; skill folders are described by their own `SKILL.md`.

## Policy Priority

When community patterns conflict with local policy, follow this order:

1. Follow explicit target project rules.
2. Maintain one `llms.txt` for every non-excluded repository directory by default.
3. Keep `.agents` excluded from directory-level coverage by default.
4. Use this skill's validator as the final gate for coverage, section shape, and links when local rules do not provide another validator.
5. Keep source summaries concise and link-based.

## Sources

- https://github.com/answerdotai/llms-txt
- https://github.com/github/awesome-copilot/blob/main/skills/create-llms/SKILL.md
- https://github.com/github/awesome-copilot/blob/main/skills/update-llms/SKILL.md
- https://github.com/github/awesome-copilot/blob/main/docs/README.skills.md
- https://github.com/microsoft/skills/blob/main/.github/plugins/deep-wiki/skills/wiki-llms-txt/SKILL.md
- https://vercel.com/docs/agent-resources/skills
- https://code.visualstudio.com/docs/agent-customization/agent-skills
