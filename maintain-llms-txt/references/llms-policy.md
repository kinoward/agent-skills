# llms.txt Policy

## Required Shape

Each `llms.txt` must use:

1. H1 on line 1.
2. Blank line on line 2.
3. Blockquote summary on line 3.
4. A short details paragraph.
5. `## Key Files`.
6. `## Boundaries`.
7. `## Validation`.
8. `## Related`.

Use relative Markdown links for repository files.

## Coverage

By default, create `llms.txt` for every repository directory except explicitly
excluded directories. Target project local rules can narrow or expand coverage.

This includes the repository root and any new top-level directory that is not in
the excluded list. When a new non-excluded directory is added, validation should
fail until that directory gets its own `llms.txt`.

Do not create `llms.txt` under excluded directories unless the target project
explicitly changes the exclusion policy.

## Excluded Directory Names

- `.git`
- `.agents`
- `node_modules`
- `.next`
- `.turbo`
- `.local`
- `dist`
- `build`
- `coverage`
- `out`
- `.cache`
- `.vercel`
- `__pycache__`
- `.pytest_cache`
- `.venv`
- `tmp`
- `generated`

## Update Triggers

- Update the same directory `llms.txt` when local files change.
- Update parent `llms.txt` files when directory purpose, important files, validation, or boundaries change.
- Update root `llms.txt` when repository-level tools, skills, apps, packages, services, docs, or major workflow rules change.
- By default, for `.agents/skills` changes, update root `llms.txt`; do not add `.agents/llms.txt`. Use script override flags only when the target project defines a different `.agents` coverage policy.

## Security

Never write token values, artifact URLs, private keys, DB URLs, production connection strings, full user media content, or other secrets into `llms.txt`.
