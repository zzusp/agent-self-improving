# Agent Self-Improving Skills

[![skills.sh](https://skills.sh/b/zzusp/agent-self-improving)](https://skills.sh/zzusp/agent-self-improving)

一组面向本机知识与记忆闭环的 Agent Skills。三个 Skill 分别负责整理资料、维护可复用认知和只读调用历史信息；数据默认保存在 `~/.agent-knowledge/`，与 Skill 代码分离。

## 包含的 Skills

| Skill | 用途 | 典型触发 |
| --- | --- | --- |
| `distill-self-improving` | 将用户明确指定的文件、目录或项目建立索引并逐份蒸馏 | “把这个项目加入知识库”“整理这批文档” |
| `evolve-self-improving` | 自动维护 user、feedback、project、reference、lesson 五类跨会话记忆与稳定知识 | “记住这条规则”“把已确认根因沉淀下来” |
| `use-self-improving` | 从 global 与当前仓库的精简 `MEMORY.md` 召回相关记忆，再按需读取主题文件 | “处理这个任务”“之前为什么这么做？” |

## 安装

可以从 GitHub/skills.sh 或 SkillHub.cn 安装。

### 从 GitHub / skills.sh 安装

需要 Node.js 和 npm。以下命令使用 [skills CLI](https://skills.sh/docs/cli) 从 GitHub 安装。

全局安装三个 Skill，供 Codex 的所有项目使用：

```powershell
npx skills@latest add zzusp/agent-self-improving --skill '*' --agent codex --global --yes
```

只安装一个 Skill：

```powershell
npx skills@latest add zzusp/agent-self-improving --skill use-self-improving --agent codex --global --yes
```

如需安装到其他受支持的 Agent，将 `codex` 替换为对应 Agent 名称；也可以省略 `--agent`，由 CLI 交互选择。省略 `--global` 时安装到当前项目。

查看仓库中可安装的 Skill：

```powershell
npx skills@latest add zzusp/agent-self-improving --list
```

### 从 SkillHub.cn 安装

国内网络可以使用 [SkillHub](https://skillhub.cn/) 安装。先按 [SkillHub 安装说明](https://skillhub.cn/install/skillhub.md) 安装 CLI；安装 Skill 时必须通过 `--dir` 指定 Codex 的全局 Skill 目录：

```powershell
skillhub install distill-self-improving --dir "$env:USERPROFILE\.codex\skills"
skillhub install evolve-self-improving --dir "$env:USERPROFILE\.codex\skills"
skillhub install use-self-improving --dir "$env:USERPROFILE\.codex\skills"
```

SkillHub 详情页：

- [distill-self-improving](https://skillhub.cn/skills/user_8cedf1d1/distill-self-improving)
- [evolve-self-improving](https://skillhub.cn/skills/user_8cedf1d1/evolve-self-improving)
- [use-self-improving](https://skillhub.cn/skills/user_8cedf1d1/use-self-improving)

安装后重新打开 Codex 会话，使新增 Skill 被发现。

### 从 ClawHub.ai 安装

OpenClaw 用户可以通过原生 Skill 命令从 [ClawHub](https://clawhub.ai/) 安装：

```powershell
openclaw skills install @zzusp/distill-self-improving
openclaw skills install @zzusp/evolve-self-improving
openclaw skills install @zzusp/use-self-improving
```

ClawHub 详情页：

- [distill-self-improving](https://clawhub.ai/zzusp/skills/distill-self-improving)
- [evolve-self-improving](https://clawhub.ai/zzusp/skills/evolve-self-improving)
- [use-self-improving](https://clawhub.ai/zzusp/skills/use-self-improving)

ClawHub 上的发布副本遵循平台规定的 MIT-0 许可；GitHub 仓库继续使用根目录中的 MIT License。

## 使用

安装后重新打开 Agent 会话，使 Skill 目录被重新发现。之后直接用自然语言提出任务即可，不必手动指定 Skill：

```text
把 D:\project\example 加入知识库，并整理其中的重要文档。
```

```text
刚才这个错误的根因已经确认，把可复用的处理方法沉淀下来。
```

```text
这个项目以前为什么选择这种部署方式？
```

需要明确指定时，也可以在支持显式调用的 Agent 中使用 `$distill-self-improving`、`$evolve-self-improving` 或 `$use-self-improving`。

三个 Skill 的协作关系是：

1. `distill-self-improving` 整理用户明确指定的原始资料，但不自动生成知识或记忆条目。
2. `evolve-self-improving` 只保存跨会话有用、来源可回查、边界清楚且无法从代码或固定指令直接推导的记忆；稳定事实进入 knowledge，已收敛方法、失败模式和护栏进入 `lesson`。
3. `use-self-improving` 先读 global 与当前仓库的一行式 `MEMORY.md`，命中后才读取 1–3 个主题文件；易变结论回到原文件、git 或当前现场复核。

## 数据与安全边界

- 原始文件保持不变；蒸馏产物、知识和记忆写入本机 `~/.agent-knowledge/`。
- 自动发现学习信号不等于自动保存；猜测、临时状态、原始报错和未定位事件不会入库。
- 查询 Skill 全程只读，不会新增、修改或删除知识库内容，也不记录访问次数。
- memory 分为 `user`、`feedback`、`project`、`reference`、`lesson`；它是可审计的上下文，不是强制规则，也不会自动下沉为 Skill、项目规则或执行门禁。
- 全局偏好进入 `memory/global/`；项目记忆按 git common dir 形成独立仓库桶，同仓库 worktree 共享，项目之间不交叉扫描。
- knowledge 与 lesson 可记录后来独立发生的复现证据；其他 memory 不统计复现次数，等价信息只追加来源并更新 `modified_at`。
- 可从当前代码、git 历史或固定项目指令直接推导的信息不写入 memory；每份 `MEMORY.md` 不超过 200 行或 25KB，主题正文按需读取。
- 凭据、隐私、客户原文和长篇原文不应写入知识库。

## 从 experience 迁移

本版本将旧 `experience/{current,archive}` 迁移为 memory 中的 `lesson`，保留正文、来源、日期、复现证据和归档状态。迁移不会猜测旧 scope 对应哪个仓库：除 `global` 外，必须用 JSON 显式提供“旧 scope → 仓库绝对路径”映射。

先执行零副作用检查：

```powershell
python evolve-self-improving/scripts/migrate_experience.py `
  --root "$env:USERPROFILE\.agent-knowledge" `
  --check `
  --scope-map "D:\path\to\scope-map.json"
```

映射文件示例：

```json
{
  "workspace:baibu-agent": "D:/baibu-agent",
  "workspace:agent-channel-host": "D:/project/agent-channel-host"
}
```

只有检查结果为 `ready` 才执行：

```powershell
python evolve-self-improving/scripts/migrate_experience.py `
  --root "$env:USERPROFILE\.agent-knowledge" `
  --apply `
  --scope-map "D:\path\to\scope-map.json"
```

成功后，原 `experience/` 与旧 `e-*` 复现文件会移动到 `legacy/experience-<UTC时间>/`，新条目使用 `m-*`、`type: lesson` 和 UTC `modified_at`。迁移结束会自动运行完整 root 校验；任何失败都会恢复迁移前状态。

## 更新与卸载

```powershell
npx skills@latest update --global
npx skills@latest remove distill-self-improving evolve-self-improving use-self-improving --global --yes
```

更多安装信息与收录状态见 [skills.sh/zzusp/agent-self-improving](https://skills.sh/zzusp/agent-self-improving)。
