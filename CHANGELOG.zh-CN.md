# 更新日志

[English](./CHANGELOG.md) · **简体中文**

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [1.2.0] - 2026-11-27

### 新增

- `session-cleanup` skill：为会话收尾，包括完成范围内的遗留事项、修正文档漂移、提交本会话产生的改动、将临时文件移入废纸篓并报告其占用空间，最后再次检查；不会移动任何会话记录
- README（`README.zh-CN.md`）和更新日志（`CHANGELOG.zh-CN.md`）的简体中文版本

### 变更

- 重新设计 README：加入徽章、按类别分组的 skill 目录、展示各 skill 协同关系的示意图、环境要求表以及仓库结构

## [1.1.0] - 2026-11-26

### 新增

- `git-commit-to-main` skill：本地拆分提交并 fast-forward 合并到 main 的工作流
- `distill-session-history` skill：将 agent 会话历史提炼为可长期保留的项目知识
- `reconcile-project-docs` skill：让项目文档与对话和仓库状态保持一致
- `maintain-llms-txt` skill：维护并校验 `llms.txt` 导航文件
- `maintain-release-version` skill：维护发布版本和更新日志条目
- `maintain-todo-md` skill：维护并校验 `TODO.md` 任务列表

## [1.0.0] - 2026-03-22

### 新增

- `mise-guide` skill：指导 agent 使用 mise 管理开发工具版本、环境变量和项目任务

[1.2.0]: https://github.com/kinoward/agent-skills/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/kinoward/agent-skills/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/kinoward/agent-skills/releases/tag/v1.0.0
