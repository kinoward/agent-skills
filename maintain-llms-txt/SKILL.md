---
name: maintain-llms-txt
description: 'Maintain repository llms.txt navigation files using the llms.txt specification, this skill''s default coverage policy, and target project local rules. Use when creating, updating, reviewing, validating, or locating llms.txt files after code, docs, config, service, package, API, or architecture changes.'
---

# Maintain llms.txt

## Overview

Use this skill to keep a target repository's directory-level `llms.txt` files accurate, concise, and useful for future agents. The workflow follows the community `llms.txt` structure and this skill's default coverage policy unless the target project defines local rules.

## Quick Start

1. Locate affected files:
   ```bash
   TARGET_REPO="$PWD"
   SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/maintain-llms-txt"
   python "$SKILL_DIR/scripts/affected_llms.py" --repo "$TARGET_REPO" --git working
   ```
2. Review the listed `primary` and `parents` `llms.txt` files.
3. Update content using `assets/llms-template.md` as the shape guide.
4. Validate:
   ```bash
   python "$SKILL_DIR/scripts/validate_llms.py" --repo "$TARGET_REPO"
   ```

## Workflow

### Locate

- For working tree changes, run `scripts/affected_llms.py --repo <target-repo> --git working`.
- For staged changes, run `scripts/affected_llms.py --repo <target-repo> --git staged`.
- For a known file list, run `scripts/affected_llms.py --repo <target-repo> --paths <file...>`.
- Treat script output as a starting point; update additional `llms.txt` files when a change affects cross-directory contracts or architecture.

### Create

- Use `assets/llms-template.md` when a non-excluded directory is missing `llms.txt`.
- Analyze the directory purpose before writing; include only files that help future agents understand ownership, boundaries, validation, or entry points.
- Create directory-level navigation files by default. Do not replace the target repository's local coverage model with a single root-only `llms.txt` unless local rules explicitly use that model.

### Update

- Keep H1, blockquote summary, details paragraph, and H2 file-list sections.
- Keep descriptions short and specific; link to source files instead of copying their content.
- Never record tokens, artifact URLs, private keys, DB URLs, production connection strings, or user content.
- Do not create `llms.txt` under excluded directories. By default `.agents` is excluded because skill folders are self-described by `SKILL.md`; use the script override flags only when the target project defines a different policy.

### Quality Checklist

- Every repository link resolves and stays inside the repo.
- Descriptions explain why the linked file matters, not just what its filename says.
- Boundaries name the directory's responsibilities and prohibited ownership.
- Validation lists commands or checks that apply to that directory.
- Content summarizes; it must not copy source files, README sections, or user data.

### Validate

- Run project validation with `scripts/validate_llms.py --repo <target-repo>`.
- Run `git diff --check`.
- If coverage fails, add the missing `llms.txt` or update the exclusion policy before finishing.
- If link checks fail, fix the target, remove the stale link, or replace it with the moved path.
- If section checks fail, restore `## Key Files`, `## Boundaries`, `## Validation`, and `## Related`.
- Do not run skill self-validation such as `quick_validate.py` merely because this skill was used; run it only when editing this skill folder.

## External References

- GitHub `create-llms` and `update-llms` are useful for repository analysis and concise link descriptions.
- Microsoft `wiki-llms-txt`, Vercel `geistdocs`, and root-only `llms.txt` generators are references only; they do not replace the target repository's local coverage rules or this skill's validator by default.

## Resources

- Read `references/community-sources.md` when you need the community rationale.
- Read `references/llms-policy.md` before changing coverage, exclusion, section, or link rules.
- Use `assets/llms-template.md` for new files.

## Commands

```bash
TARGET_REPO="$PWD"
SKILL_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}/maintain-llms-txt"
python "$SKILL_DIR/scripts/affected_llms.py" --repo "$TARGET_REPO" --paths AGENTS.md TODO.md
python "$SKILL_DIR/scripts/affected_llms.py" --repo "$TARGET_REPO" --git working
python "$SKILL_DIR/scripts/validate_llms.py" --repo "$TARGET_REPO"
```
