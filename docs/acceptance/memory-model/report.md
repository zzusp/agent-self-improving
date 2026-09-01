# Memory model 验收报告

## 结论

源码与 fixture 验收全绿：memory 已成为 experience 的超集，保留 `lesson` 学习；global 与 repository memory 物理隔离；同仓库 worktree 解析到相同 identity；索引含 tags 并执行 200 行/25KB 双门禁；legacy 迁移支持零副作用检查、显式 scope map、正文/复现保留、备份和失败回滚。

## 证据

- 13 个 unittest 全部通过。
- 3 个 Python 文件 AST 解析通过。
- staged diff whitespace 检查通过。
- 当前真实数据 `--check` 扫描 59 条 experience，汇总 22 个唯一 scope blocker，根目录清单未变化。

## 未执行项

- 未对当前本机真实数据执行 `--apply`；缺少 22 个 scope 的仓库路径确认。
- 未发布新 Skill 版本，也未验证 skills.sh、SkillHub 或 ClawHub 安装后的运行态。

因此本报告只证明源码、CLI fixture 和真实数据只读预检，不声称已完成用户数据迁移或发布部署。
