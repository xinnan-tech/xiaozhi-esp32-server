# CRM 用户故事与 30 个自动化测试用例

## 用户故事

作为门店店长，我希望客户完成语音反馈后，系统能通过手机号后四位识别客户，并自动把客户反馈关联到客户档案、到店记录、建议管理、问题修复和账户流水；同时我能在统计概览中按员工查看好评、中评、差评，用作员工 KPI 管理。

## 验收标准

1. 客户档案支持麦凯66字段，且字段数为66。
2. 可按手机号/姓名搜索客户。
3. 客户反馈可通过手机号后四位自动匹配客户。
4. 客户反馈可自动创建/关联到店记录，并同步满意度、员工、项目、到店时间。
5. 反馈建议自动进入建议管理，并支持去重、采纳、处理说明。
6. 差评/退款/销卡/投诉类反馈自动进入问题修复。
7. 账户消费如果没填到店记录，自动关联客户最近一次到店，并同步消费金额。
8. 店长可在统计概览看到员工好评、中评、差评 KPI，并查看评价明细。
9. 系统提供 CLI，方便 AI Agent 管理系统。

## 30 个自动化测试用例

1. 麦凯66字段数量等于66。
2. 麦凯66字段 key 不重复。
3. 创建客户并写入麦凯66字段。
4. 按手机号搜索客户。
5. 更新客户健康档案。
6. 创建到店记录并自动计算耗时。
7. 到店记录返回客户姓名。
8. 创建到店后更新客户累计到店统计。
9. 开卡/建账户自动生成充值流水。
10. 账户消费后剩余次数减少。
11. 账户消费自动生成消费流水。
12. 消费未传到店记录时自动关联最近到店。
13. 消费金额同步回到店记录。
14. 创建客户建议。
15. 重复建议自动去重并增加 frequency。
16. 采纳建议并保存处理说明。
17. 创建问题修复记录。
18. 标记问题已修复并自动记录修复时间。
19. 销卡后账户状态变为已销卡。
20. 销卡原因不满意/退款时自动生成问题。
21. 反馈记录可绑定客户和到店记录。
22. 员工 KPI 正确统计好/中/差评。
23. 员工评价明细可筛选差评。
24. 从文本中提取手机号后四位。
25. 反馈自动通过手机号后四位匹配客户。
26. 反馈自动创建到店记录。
27. 反馈自动创建建议。
28. 差评反馈自动创建问题修复。
29. 客户详情聚合到店、账户、流水、建议、问题。
30. CRM 看板统计客户、到店、销卡、建议、问题数量。

## 执行命令

```bash
cd main/feedback-backend
PYTHONPATH=. python -m unittest discover -s tests -v
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="main/feedback-backend"
python -m unittest discover -s "main/feedback-backend/tests" -v
```

## CLI 示例

```bash
python main/feedback-backend/cli.py login --username admin --password admin123
python main/feedback-backend/cli.py --token <JWT> crm overview
python main/feedback-backend/cli.py --token <JWT> crm member-list --keyword 1234
python main/feedback-backend/cli.py --token <JWT> stats employee-kpi
```
