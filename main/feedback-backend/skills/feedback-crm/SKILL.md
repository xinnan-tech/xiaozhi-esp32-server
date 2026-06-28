---
name: feedback-crm
description: 通过 CLI 管理反馈系统、CRM、员工KPI、建议和问题修复。适合 AI Agent 调用后台系统能力。
---

# Feedback CRM Skill

该 skill 将后台系统能力收敛到 `cli.py`，AI Agent 应优先通过 CLI 调用系统，而不是直接操作数据库。

## 环境变量

```bash
export FEEDBACK_API_BASE="https://feedback-admin.new123.vip/api/v1"
export FEEDBACK_TOKEN="<JWT>"
```

获取 token：

```bash
python main/feedback-backend/cli.py --base-url "$FEEDBACK_API_BASE" login --username admin --password admin123 --raw-token
```

## 常用能力

### 健康检查

```bash
python main/feedback-backend/cli.py health
```

### 查 CRM 概览

```bash
python main/feedback-backend/cli.py crm overview
```

### 查客户

```bash
python main/feedback-backend/cli.py crm member-list --keyword 1234
python main/feedback-backend/cli.py crm member-detail --member-id <member_id>
```

### 创建/更新客户

```bash
python main/feedback-backend/cli.py crm member-create --name 张女士 --phone 13800001234 --health 肩颈酸痛
python main/feedback-backend/cli.py crm member-update --member-id <member_id> --level VIP
```

复杂客户档案用 JSON：

```bash
python main/feedback-backend/cli.py crm member-create --json-file member.json
```

### 到店记录

```bash
python main/feedback-backend/cli.py crm visit-list --member-id <member_id>
python main/feedback-backend/cli.py crm visit-create --member-id <member_id> --employee-id <employee_id> --arrive-at 2026-06-20T10:00:00 --items 肩颈调理
```

### 账户/卡/流水

```bash
python main/feedback-backend/cli.py crm account-list --member-id <member_id>
python main/feedback-backend/cli.py crm account-create --member-id <member_id> --card-name 肩颈10次卡 --account-type count --amount 1000 --count 10
python main/feedback-backend/cli.py crm account-consume --account-id <account_id> --count 1 --notes 消费1次
python main/feedback-backend/cli.py crm transactions --member-id <member_id>
```

### 销卡

```bash
python main/feedback-backend/cli.py crm card-close --account-id <account_id> --reason 服务不满意要求退款 --refund-amount 100 --assigned-to 店长
python main/feedback-backend/cli.py crm card-close-list --member-id <member_id>
```

### 建议管理

```bash
python main/feedback-backend/cli.py crm suggestion-list --status pending
python main/feedback-backend/cli.py crm suggestion-create --content 希望提前开空调 --category environment
python main/feedback-backend/cli.py crm suggestion-status --suggestion-id <id> --status adopted --notes 服务前30分钟开空调
```

### 问题修复

```bash
python main/feedback-backend/cli.py crm issue-list --status identified
python main/feedback-backend/cli.py crm issue-create --title 房间温度偏低 --severity medium --assigned-to 店长
python main/feedback-backend/cli.py crm issue-fix --issue-id <id> --result 已增加毛毯并提前开空调
python main/feedback-backend/cli.py crm issue-close --issue-id <id> --result 店长复核通过
```

### 反馈和 KPI

```bash
python main/feedback-backend/cli.py feedback record-list --employee-id <employee_id> --satisfaction very_bad
python main/feedback-backend/cli.py stats employee-kpi
python main/feedback-backend/cli.py stats employee-records --employee-id <employee_id> --group bad
```

### 模拟反馈处理

会调用 LLM，谨慎使用：

```bash
python main/feedback-backend/cli.py feedback process --store-name 腰妍美容养生馆 --employee-number 1 --text "手机号后四位1234，今天肩颈调理，房间有点冷，希望提前开空调" --satisfaction satisfied --store-id store001 --employee-id emp001
```

## 操作原则

1. 只读查询可直接执行。
2. 创建/更新/销卡/修复等写操作应返回结果给用户确认。
3. 不直接删数据；如需删除，先询问用户并走后台 API。
4. 复杂 payload 优先使用 `--json-file`，便于审计。
5. 不绕过权限，使用当前用户 token 调用 API。
