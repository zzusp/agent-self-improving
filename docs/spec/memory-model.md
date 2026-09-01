# 自动记忆模型改造

> 历史方案：项目桶与 Git identity 已被 [统一记忆目录](./unified-memory.md) 取代；本文件只保留最初设计快照，不代表当前契约。

## 目标

将只覆盖方法、失败模式和护栏的 `experience` 扩展为可跨会话使用的 `memory`，同时保证 memory 是 experience 的超集：用户偏好、纠正反馈、项目决定、外部入口进入新类型，原本由错误和运行证据收敛出的可复用方法继续作为 `lesson` 保存。

## 参考边界

Claude Code 的 auto memory 采用按仓库隔离、worktree 共享的本机目录；以精简 `MEMORY.md` 作为常驻索引，主题文件按需读取；区分 `user`、`feedback`、`project`、`reference`，且不要求每次会话产生记忆。其 `MEMORY.md` 启动读取边界为 200 行或 25KB。

OpenAI 官方 Codex 文档未建立等价的 auto-memory 产品契约，因此不假设 Codex 与 Claude Code 行为相同。本项目只借鉴公开的信息架构，并通过 Skills、普通 Markdown 与本地校验工具实现。

## 数据结构

```text
~/.agent-knowledge/
├── knowledge/
│   ├── current/INDEX.md
│   └── archive/INDEX.md
├── memory/
│   ├── global/
│   │   ├── current/MEMORY.md
│   │   └── archive/INDEX.md
│   └── projects/
│       └── <slug>-<identity-sha256前12位>/
│           ├── scope.json
│           ├── current/MEMORY.md
│           └── archive/INDEX.md
├── recurrence/
└── legacy/
```

- global 只接收 `scope: global`；项目条目 scope 以 `repo:<project-key>` 开头。
- repository identity 取 `git rev-parse --path-format=absolute --git-common-dir` 的规范化绝对路径；同一仓库所有 worktree 因此共享 project key。
- `scope.json` 保存 `project_key`、`git_common_dir` 与已确认的 `roots`，召回时先按 common dir 精确匹配，不扫描其他项目。
- current memory 的索引每条一行，包含 id、type、scope、modified_at、tags、title 和特异概括；正文按需读取。
- 每份 `MEMORY.md` 必须同时不超过 200 行和 25KB；超过时校验与渲染失败，要求合并或归档，不静默截断。

## 条目模型

- `user`：用户角色、专业背景和稳定工作偏好。
- `feedback`：用户纠正及明确确认有效的做法。
- `project`：无法从代码或 git 历史恢复的进行中决定、上下文和边界。
- `reference`：外部系统、文档、看板或权威入口的定位与核验方法。
- `lesson`：correction、feature-request、knowledge-gap 或 error 经证据闭环形成的可复用方法、失败模式和护栏。

memory 使用 `m-` id，正文有效字符 40–800，`modified_at` 为 UTC 秒级时间。knowledge 继续使用 `k-` id和 300–400 字证据摘要。knowledge 与 lesson 可以关联独立复现证据；其他类型不以复现次数制造权重。

不保存可从当前代码、git 历史或项目指令直接推导的内容，也不保存临时诉求、猜测、原始错误、敏感信息和每轮任务摘要。

## Legacy 迁移

- `migrate_experience.py --check` 是零副作用预检；缺 source、格式错误、孤儿复现、目标 memory 已存在或非 global scope 未映射时阻断。
- scope map 必须把每个旧项目 scope 映射到仓库绝对路径；工具据 git common dir 生成稳定项目桶，不按字符串猜仓库。
- `--apply` 将 `e-*` 确定性转换为 `m-* + type: lesson`，保留正文、来源、日期、归档状态和复现文件；成功后把旧数据移动到 `legacy/experience-<UTC时间>/`。
- 写入前在临时目录构建并校验全部条目、复现与索引；安装后再运行 root 校验，失败则恢复旧目录和复现文件。

## 验证矩阵

- 五类 memory 均可通过 schema；未知 type、错误物理 scope 和非 UTC `modified_at` 必须失败。
- global 与项目桶独立，git worktree 解析到同一 project key。
- tags 出现在 `MEMORY.md`，支持 tag-only 召回。
- 200 行和 25KB 两项边界均由校验器拒绝。
- root 校验显式拒绝未迁移 `experience/`。
- migration check 无写入；apply 保留 lesson 正文、复现与备份，结束后的完整 root 校验通过。
