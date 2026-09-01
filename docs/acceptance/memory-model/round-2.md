# Round 2

## 目标

在当前本机真实旧数据上完成迁移，并修复真实预检暴露的两类模型缺口：明确项目根不是 Git 仓库时仍能形成隔离项目桶；已有 `k-*` knowledge 复现不应被 legacy `e-*` 迁移预检误判为孤儿。

## 缺口与修正

- 旧数据的主要作用域属于一个明确的非 Git 工作区。迁移器原先只接受 Git common dir，无法忠实定位该项目；现增加目录 identity，使用规范化绝对工作区根生成 project key，`scope.json.git_common_dir` 为 null。
- 真实 `recurrence/` 同时存在 `e-*` 与合法 `k-*`。原预检用 legacy id 集合校验全部复现文件，导致 `k-*` 假孤儿；现只在迁移预检读取 `e-*.md`，安装后仍由 root 校验器完整检查所有 knowledge 与 lesson 复现。

## 自动化验证

执行：

```powershell
python -B -m unittest discover -s evolve-self-improving\tests -v
```

结果：15 个测试全部通过。新增覆盖非 Git 工作区 identity、`git_common_dir: null` 的项目桶校验，以及迁移预检不误报非 legacy 复现。

## 真实数据预检与迁移

使用 22 个旧 scope 的精确临时映射执行 `migrate_experience.py --check`：

- `status=ready`、退出码 0；
- 扫描并计划 59 条，形成 3 个项目桶；
- 识别 1 个 legacy 复现，blocker 为 0；
- 检查前后数据根清单一致，未出现 `memory/`、`legacy/` 或 staging 残留。

随后在用户明确授权下执行 `--apply`，返回 `status=pass`，旧目录备份到 `~/.agent-knowledge/legacy/experience-20260901T045151Z/`。

## 独立读回

- `validate_entries.py check --root ... --json`：88 个 knowledge + memory 条目，0 failure；2 个复现文件、3 条复现记录。
- legacy 与 memory 逐条比较：59/59 个新 id 唯一存在；正文、title、tags、learned_at、source、lesson type、UTC modified_at 与保留的旧 scope 后缀均一致，0 mismatch。
- 1 个 `e-*` 复现的 id 和标题完成确定性转换，内容一致；原有 `k-*` 复现仍存在。
- 三个 current 项目索引分别为 10 行/3034 字节、53 行/22522 字节、8 行/2230 字节，均低于 200 行/25KB；global current 为 4 行/117 字节。
- `experience/` 已不存在，staging 残留为 0，旧数据可从带 UTC 时间戳的 legacy 备份回查。

## 边界

本轮完成的是本机认知数据迁移和源码回归，不代表新 Skill 已发布到 skills.sh、SkillHub、ClawHub 或已部署到其他 Agent 运行环境。本地数据根既有长篇 `README.md` 仍是旧版本契约文本；迁移器没有在缺少可验证模板版本时静默覆盖用户文档，仓库级 README 与两个 Skill 已更新为新契约。
