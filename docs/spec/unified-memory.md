# 统一记忆目录

## 目标

取消按项目拆分 memory。所有记忆条目只分 `current` 与 `archive`，项目名或工作范围仅保留在条目 `scope` 字段中作为检索标签，不再决定物理目录。

## 唯一路径

```text
memory/
├── current/
│   ├── MEMORY.md
│   └── m-*.md
└── archive/
    ├── INDEX.md
    └── m-*.md
```

- 写入只判断条目是 current 还是 archive。
- 查询只读一份 `memory/current/MEMORY.md`，先按 scope 过滤，再按标题和 Agent 编写的语义 summary 选择正文。
- `scope: global` 表示跨任务适用；其他非空 scope 是稳定的逻辑标签，可使用 `workspace:*`、`domain:*`、`product:*`、`runtime:*` 等既有命名和 `/` 子范围。只有与当前逻辑 scope 完全相同或作为其父级的条目可进入候选；上下文无法确定时只使用 global。
- 不识别项目目录，不区分 Git/非 Git，不维护 project key、`scope.json`、roots、别名或临时目录规则。
- `MEMORY.md` 同时保留 200 行与 25000 bytes 上限，防止常驻索引无限增长；每条只输出 `[title](主题文件) | scope | summary`，其他字段按需从正文读取。

## 迁移

Legacy experience 的所有条目按原 current/archive 状态进入统一 memory，原 scope 原样保留，不再要求 scope map。迁移前由 Agent 逐条补齐语义 summary，迁移器只校验并保留，不从正文抽取。既有项目桶在本机迁移时合并，`repo:<project-key>/` 物理路由前缀从 scope 中移除。

## 验证

- 五类 memory 和任意非空 scope 均可写入同一 current/archive 目录。
- `memory/global`、`memory/projects` 与 `scope.json` 不再属于有效根结构。
- legacy 非 global scope 无需目录映射即可迁移且原样保留。
- 本机现有条目合并后 id 不冲突，完整 root 校验为零失败。

## 延后升级条件

只有 active memory 超过 200 行或 25000 bytes 且经摘要改写、去重、合并、归档仍无法收敛，或出现有证据的跨 scope 误召回，才重新评估索引分片。没有这两类事实前不增加物理隔离。
