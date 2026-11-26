# Community Sources

This skill follows community task-list conventions while staying lightweight.

## Adopted

- `todomd/todo.md`: keep a repo-local `TODO.md`, group tasks by section, and treat sections as lightweight workflow columns.
- `todo-md` CLI conventions: keep task files small, plain text, and easy to review in git.
- GitHub task lists: use GitHub Flavored Markdown checkboxes so tasks render naturally in GitHub-compatible viewers.
- todo.txt: borrow the idea of lightweight inline metadata, but only use fields allowed by this skill's default policy or the target project's local rules.

## Not Adopted

- Do not introduce a separate CLI dependency.
- Do not require todo.txt canonical line format.
- Do not split completed items into another file unless the user explicitly asks.
- Do not use `- [-]` declined items by default because this skill prefers GitHub-compatible checkbox rendering.
- Do not allow arbitrary section names or multiple project files by default.
- Do not make `TODO.md` a replacement for GitHub Issues, ADRs, or feature specifications.
- Do not adopt optional checkbox syntax by default; this skill uses `- [ ]` and `- [x]`.

## Policy Priority

When community formats conflict with local policy, follow this order:

1. Follow explicit target project rules.
2. Keep one root `TODO.md` by default.
3. Keep the default sections `Next`, `Backlog`, `Blocked`, and `Done ✓`.
4. Keep open tasks outside `Done ✓` and completed tasks inside `Done ✓`.
5. Use only `#tag`, known `@owner`, `+project`, and real `due:YYYY-MM-DD` metadata unless local rules say otherwise.
6. Run this skill's validator before finishing when local rules do not provide another validator.

## Sources

- https://github.com/todomd/todo.md
- https://hypercubed.github.io/todo-md/
- https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists
- https://todotxt.org/
