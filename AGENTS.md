# xiaozhi-esp32-server — Agent 指南

## PR 问题归属（GitHub Issues 唯一正本）

- 每个 PR（包括 Draft、文档和依赖更新）必须在正文以独立纯文本行填写 `主 Issue：完整 GitHub Issue URL`、`补充此前 PR：无或完整 PR URL`、`本次解决：具体范围`。模板中的示例或注释不算声明。
- 新工作先搜索开放及已关闭 Issues；同一根因、目标和验收范围复用原 Issue。补充此前 PR 时必须继承其主 Issue；旧 PR 没有声明则先补齐旧 PR，不能另建重复 Issue。允许引用已关闭 Issue，不为过门禁重开或新建。
- 跨仓共用协调仓的一条 Issue，不使用 H/OI 平行编号。`OPEN_ISSUE.md` / `OPEN_ISSUES.md` 只作导航和冻结历史，禁止新增台账正文；讨论、状态、证据和验收只更新 GitHub Issue。
- 创建和合并使用母仓已审查 `origin/main` 的统一 PR 策略；CI 验证当前正文、真实 Issue 和补充继承。API/权限失败即阻断，旧绿色 CI 不能代替合并前重新读取。跨仓访问使用已有只读授权，不复制个人凭据。
- 审查还需确认“本次解决”确实属于该 Issue，以及是否漏报补充关系；机械校验不能证明这些语义。多个 PR 可以对应一个 Issue；仅全部验收完成时才使用关闭关键字或关闭 Issue。

接入与验收范围：[母仓 Issue #897](https://github.com/zebbingo/zebbingo-ai-agent/issues/897)。创建、CI、合并的当前证据以该 Issue 及关联 PR 为准。
