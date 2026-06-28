#!/usr/bin/env python3
"""Feedback/CRM CLI.

面向人工和 AI Agent 的命令行入口，统一调用后台 HTTP API。

常用示例：
  python cli.py login --username admin --password admin123 --raw-token
  python cli.py --token <JWT> crm overview
  python cli.py --token <JWT> crm member-list --keyword 1234
  python cli.py --token <JWT> stats employee-kpi
  python cli.py --token <JWT> crm issue-fix --issue-id <ID> --result 已处理

环境变量：
  FEEDBACK_API_BASE=http://127.0.0.1:8007/api/v1
  FEEDBACK_TOKEN=<JWT>
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = os.environ.get("FEEDBACK_API_BASE", "http://127.0.0.1:8007/api/v1")
DEFAULT_TOKEN = os.environ.get("FEEDBACK_TOKEN", "")


# ---- HTTP / IO ----

def request(method, path, token="", data=None, params=None, base_url=DEFAULT_BASE_URL):
    url = base_url.rstrip("/") + path
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        if query:
            url += "?" + query
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code}: {text}")
    except urllib.error.URLError as e:
        raise SystemExit(f"请求失败: {e}")


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def require_token(args):
    token = args.token or DEFAULT_TOKEN
    if not token:
        raise SystemExit("缺少 token：请传 --token 或设置 FEEDBACK_TOKEN，或先执行 login")
    return token


def load_json_file(path):
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_payload(args, base=None):
    payload = dict(base or {})
    payload.update(load_json_file(getattr(args, "json_file", "")))
    return {k: v for k, v in payload.items() if v not in (None, "", [])}


def split_list(value):
    if not value:
        return []
    return [x.strip() for x in value.replace("，", ",").split(",") if x.strip()]


# ---- Basic ----

def cmd_login(args):
    data = request("POST", "/auth/login", data={"username": args.username, "password": args.password}, base_url=args.base_url)
    if args.raw_token:
        print(data.get("access_token", ""))
    elif args.export:
        print(f"$env:FEEDBACK_TOKEN='{data.get('access_token', '')}'")
    else:
        print_json(data)


def cmd_health(args):
    base = args.base_url.rsplit("/api/v1", 1)[0]
    print_json(request("GET", "/health", base_url=base))


# ---- CRM ----

def cmd_crm_overview(args):
    print_json(request("GET", "/crm/overview", token=require_token(args), base_url=args.base_url))


def cmd_crm_mekai66(args):
    print_json(request("GET", "/crm/mekai66-fields", token=require_token(args), base_url=args.base_url))


def cmd_member_list(args):
    print_json(request("GET", "/crm/member/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "keyword": args.keyword, "status": args.status,
    }))


def cmd_member_detail(args):
    print_json(request("GET", f"/crm/member/{args.member_id}", token=require_token(args), base_url=args.base_url))


def cmd_member_create(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "name": args.name,
        "phone": args.phone,
        "wechat": args.wechat,
        "level": args.level,
        "beautyConcerns": split_list(args.beauty),
        "healthIssues": split_list(args.health),
        "allergies": args.allergies,
        "notes": args.notes,
    })
    print_json(request("POST", "/crm/member", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_member_update(args):
    payload = merge_payload(args, {
        "name": args.name,
        "phone": args.phone,
        "wechat": args.wechat,
        "level": args.level,
        "beautyConcerns": split_list(args.beauty),
        "healthIssues": split_list(args.health),
        "allergies": args.allergies,
        "notes": args.notes,
        "status": args.status,
    })
    print_json(request("PUT", f"/crm/member/{args.member_id}", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_visit_list(args):
    print_json(request("GET", "/crm/visit/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "member_id": args.member_id,
    }))


def cmd_visit_create(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "memberId": args.member_id,
        "employeeId": args.employee_id,
        "arriveAt": args.arrive_at,
        "leaveAt": args.leave_at,
        "serviceItems": split_list(args.items),
        "consumptionAmount": args.amount,
        "satisfaction": args.satisfaction,
        "notes": args.notes,
    })
    print_json(request("POST", "/crm/visit", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_visit_update(args):
    payload = merge_payload(args, {
        "memberId": args.member_id,
        "employeeId": args.employee_id,
        "arriveAt": args.arrive_at,
        "leaveAt": args.leave_at,
        "serviceItems": split_list(args.items),
        "consumptionAmount": args.amount,
        "satisfaction": args.satisfaction,
        "notes": args.notes,
    })
    print_json(request("PUT", f"/crm/visit/{args.visit_id}", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_account_list(args):
    print_json(request("GET", "/crm/account/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "member_id": args.member_id, "status": args.status,
    }))


def cmd_account_create(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "memberId": args.member_id,
        "accountType": args.account_type,
        "cardName": args.card_name,
        "totalAmount": args.amount,
        "totalCount": args.count,
        "validStart": args.valid_start,
        "validEnd": args.valid_end,
        "notes": args.notes,
    })
    print_json(request("POST", "/crm/account", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_account_consume(args):
    payload = merge_payload(args, {
        "amount": args.amount,
        "countChange": args.count,
        "visitId": args.visit_id,
        "notes": args.notes,
    })
    print_json(request("POST", f"/crm/account/{args.account_id}/consume", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_transactions(args):
    print_json(request("GET", "/crm/account/transactions", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "account_id": args.account_id, "member_id": args.member_id,
    }))


def cmd_body_status_list(args):
    print_json(request("GET", "/crm/body-status/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "member_id": args.member_id,
    }))


def cmd_body_status_create(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "memberId": args.member_id,
        "visitId": args.visit_id,
        "memberProductId": args.member_product_id,
        "weight": args.weight,
        "waistline": args.waistline,
        "painLevel": args.pain_level,
        "sleepQuality": args.sleep_quality,
        "skinStatus": args.skin_status,
        "notes": args.notes,
    })
    print_json(request("POST", "/crm/body-status", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_product_list(args):
    print_json(request("GET", "/crm/product/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "keyword": args.keyword, "category": args.category, "status": args.status,
    }))


def cmd_product_create(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "productName": args.product_name,
        "productType": args.product_type,
        "category": args.category,
        "price": args.price,
        "defaultCount": args.default_count,
        "description": args.description,
    })
    print_json(request("POST", "/crm/product", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_member_product_list(args):
    print_json(request("GET", "/crm/member-product/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "member_id": args.member_id, "status": args.status,
    }))


def cmd_product_purchase(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "memberId": args.member_id,
        "productId": args.product_id,
        "productName": args.product_name,
        "totalCount": args.total_count,
        "totalAmount": args.total_amount,
        "validStart": args.valid_start,
        "validEnd": args.valid_end,
        "notes": args.notes,
    })
    print_json(request("POST", "/crm/member-product/purchase", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_product_consume(args):
    payload = merge_payload(args, {
        "consumeCount": args.consume_count,
        "consumeAmount": args.consume_amount,
        "visitId": args.visit_id,
        "notes": args.notes,
    })
    print_json(request("POST", f"/crm/member-product/{args.member_product_id}/consume", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_product_consumes(args):
    print_json(request("GET", "/crm/product-consume/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "member_id": args.member_id, "member_product_id": args.member_product_id,
    }))


def cmd_card_close(args):
    payload = merge_payload(args, {
        "accountId": args.account_id,
        "reason": args.reason,
        "refundAmount": args.refund_amount,
        "feedbackRecordId": args.feedback_id,
        "assignedTo": args.assigned_to,
        "handleNotes": args.notes,
    })
    print_json(request("POST", "/crm/card-close", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_card_close_list(args):
    print_json(request("GET", "/crm/card-close/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "member_id": args.member_id,
    }))


def cmd_suggestion_list(args):
    print_json(request("GET", "/crm/suggestion/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "status": args.status,
    }))


def cmd_suggestion_create(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "memberId": args.member_id,
        "feedbackRecordId": args.feedback_id,
        "content": args.content,
        "category": args.category,
    })
    print_json(request("POST", "/crm/suggestion", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_suggestion_status(args):
    payload = merge_payload(args, {
        "status": args.status,
        "handleNotes": args.notes,
        "rejectedReason": args.rejected_reason,
    })
    print_json(request("POST", f"/crm/suggestion/{args.suggestion_id}/status", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_issue_list(args):
    print_json(request("GET", "/crm/issue/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "status": args.status,
    }))


def cmd_issue_create(args):
    payload = merge_payload(args, {
        "storeId": args.store_id,
        "memberId": args.member_id,
        "feedbackRecordId": args.feedback_id,
        "cardCloseId": args.card_close_id,
        "title": args.title,
        "description": args.description,
        "severity": args.severity,
        "category": args.category,
        "assignedTo": args.assigned_to,
        "fixPlan": args.fix_plan,
        "fixDeadline": args.fix_deadline,
    })
    print_json(request("POST", "/crm/issue", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_issue_update(args):
    payload = merge_payload(args, {
        "title": args.title,
        "description": args.description,
        "severity": args.severity,
        "category": args.category,
        "status": args.status,
        "assignedTo": args.assigned_to,
        "fixPlan": args.fix_plan,
        "fixResult": args.fix_result,
    })
    print_json(request("PUT", f"/crm/issue/{args.issue_id}", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_issue_fix(args):
    payload = merge_payload(args, {"status": "fixed", "fixResult": args.result, "fixPlan": args.plan})
    print_json(request("PUT", f"/crm/issue/{args.issue_id}", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_issue_close(args):
    payload = merge_payload(args, {"status": "closed", "fixResult": args.result})
    print_json(request("PUT", f"/crm/issue/{args.issue_id}", token=require_token(args), base_url=args.base_url, data={"data": payload}))


def cmd_feedback_bind(args):
    payload = merge_payload(args, {
        "memberId": args.member_id,
        "visitId": args.visit_id,
        "cardCloseId": args.card_close_id,
    })
    print_json(request("POST", f"/crm/feedback/{args.feedback_id}/bind", token=require_token(args), base_url=args.base_url, data={"data": payload}))


# ---- Feedback / Store / Employee / Stats ----

def cmd_record_list(args):
    print_json(request("GET", "/record/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page,
        "page_size": args.page_size,
        "store_id": args.store_id,
        "employee_id": args.employee_id,
        "satisfaction": args.satisfaction,
        "start_date": args.start_date,
        "end_date": args.end_date,
    }))


def cmd_feedback_process(args):
    payload = merge_payload(args, {
        "storeName": args.store_name,
        "employeeNumber": args.employee_number,
        "asrText": args.text,
        "sessionId": args.session_id,
        "deviceMac": args.device_mac,
        "satisfaction": args.satisfaction,
        "storeId": args.store_id,
        "employeeId": args.employee_id,
    })
    print_json(request("POST", "/public/process", base_url=args.base_url, data=payload))


def cmd_store_list(args):
    print_json(request("GET", "/store/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "keyword": args.keyword,
    }))


def cmd_employee_list(args):
    print_json(request("GET", "/employee/list", token=require_token(args), base_url=args.base_url, params={
        "page": args.page, "page_size": args.page_size, "store_id": args.store_id,
    }))


def cmd_employee_kpi(args):
    print_json(request("GET", "/stats/employee-kpi", token=require_token(args), base_url=args.base_url, params={
        "start_date": args.start_date, "end_date": args.end_date,
    }))


def cmd_employee_records(args):
    print_json(request("GET", "/stats/employee-records", token=require_token(args), base_url=args.base_url, params={
        "employee_id": args.employee_id,
        "satisfaction_group": args.group,
        "page": args.page,
        "page_size": args.page_size,
    }))


def cmd_raw(args):
    data = load_json_file(args.json_file) if args.json_file else None
    print_json(request(args.method, args.path, token=(args.token or DEFAULT_TOKEN), data=data, base_url=args.base_url))


# ---- Parser ----

def add_common(parser):
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL，默认 {DEFAULT_BASE_URL}")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="JWT token；也可用 FEEDBACK_TOKEN")


def add_json_file(parser):
    parser.add_argument("--json-file", default="", help="从 JSON 文件读取 data，并覆盖/补充命令行参数")


def add_page(parser):
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)


def build_parser():
    parser = argparse.ArgumentParser(description="Feedback/CRM CLI")
    add_common(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("login", help="登录并输出 token")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--raw-token", action="store_true", help="只输出 token，便于脚本使用")
    p.add_argument("--export", action="store_true", help="输出 PowerShell 环境变量设置语句")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("health", help="健康检查")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("raw", help="原始 HTTP 调用，高级/AI 用")
    p.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "DELETE"])
    p.add_argument("--path", required=True, help="例如 /crm/overview")
    p.add_argument("--json-file", default="")
    p.set_defaults(func=cmd_raw)

    crm = sub.add_parser("crm", help="CRM 命令")
    crm_sub = crm.add_subparsers(dest="crm_command", required=True)

    p = crm_sub.add_parser("overview", help="CRM 看板")
    p.set_defaults(func=cmd_crm_overview)

    p = crm_sub.add_parser("mekai66-fields", help="查看麦凯66字段")
    p.set_defaults(func=cmd_crm_mekai66)

    p = crm_sub.add_parser("member-list", help="客户列表")
    p.add_argument("--keyword", default="")
    p.add_argument("--status", type=int)
    add_page(p)
    p.set_defaults(func=cmd_member_list)

    p = crm_sub.add_parser("member-detail", help="客户详情")
    p.add_argument("--member-id", required=True)
    p.set_defaults(func=cmd_member_detail)

    p = crm_sub.add_parser("member-create", help="创建客户")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--name", default="")
    p.add_argument("--phone", default="")
    p.add_argument("--wechat", default="")
    p.add_argument("--level", default="")
    p.add_argument("--beauty", default="", help="逗号分隔")
    p.add_argument("--health", default="", help="逗号分隔")
    p.add_argument("--allergies", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_member_create)

    p = crm_sub.add_parser("member-update", help="更新客户")
    add_json_file(p)
    p.add_argument("--member-id", required=True)
    p.add_argument("--name", default="")
    p.add_argument("--phone", default="")
    p.add_argument("--wechat", default="")
    p.add_argument("--level", default="")
    p.add_argument("--beauty", default="")
    p.add_argument("--health", default="")
    p.add_argument("--allergies", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--status", type=int)
    p.set_defaults(func=cmd_member_update)

    p = crm_sub.add_parser("visit-list", help="到店记录列表")
    p.add_argument("--member-id", default="")
    add_page(p)
    p.set_defaults(func=cmd_visit_list)

    p = crm_sub.add_parser("visit-create", help="创建到店记录")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--member-id", default="")
    p.add_argument("--employee-id", default="")
    p.add_argument("--arrive-at", default="")
    p.add_argument("--leave-at", default="")
    p.add_argument("--items", default="")
    p.add_argument("--amount", default="0")
    p.add_argument("--satisfaction", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_visit_create)

    p = crm_sub.add_parser("visit-update", help="更新到店记录")
    add_json_file(p)
    p.add_argument("--visit-id", required=True)
    p.add_argument("--member-id", default="")
    p.add_argument("--employee-id", default="")
    p.add_argument("--arrive-at", default="")
    p.add_argument("--leave-at", default="")
    p.add_argument("--items", default="")
    p.add_argument("--amount", default="")
    p.add_argument("--satisfaction", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_visit_update)

    p = crm_sub.add_parser("account-list", help="账户列表")
    p.add_argument("--member-id", default="")
    p.add_argument("--status", type=int)
    add_page(p)
    p.set_defaults(func=cmd_account_list)

    p = crm_sub.add_parser("account-create", help="开卡/建账户")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--member-id", default="")
    p.add_argument("--account-type", default="balance")
    p.add_argument("--card-name", default="")
    p.add_argument("--amount", default="0")
    p.add_argument("--count", default="0")
    p.add_argument("--valid-start", default="")
    p.add_argument("--valid-end", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_account_create)

    p = crm_sub.add_parser("account-consume", help="账户消费")
    add_json_file(p)
    p.add_argument("--account-id", required=True)
    p.add_argument("--amount", default="0")
    p.add_argument("--count", default="0")
    p.add_argument("--visit-id", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_account_consume)

    p = crm_sub.add_parser("transactions", help="账户流水")
    p.add_argument("--account-id", default="")
    p.add_argument("--member-id", default="")
    add_page(p)
    p.set_defaults(func=cmd_transactions)

    p = crm_sub.add_parser("body-status-list", help="身体变化记录")
    p.add_argument("--member-id", default="")
    add_page(p)
    p.set_defaults(func=cmd_body_status_list)

    p = crm_sub.add_parser("body-status-create", help="创建身体变化记录")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--member-id", default="")
    p.add_argument("--visit-id", default="")
    p.add_argument("--member-product-id", default="")
    p.add_argument("--weight", default="")
    p.add_argument("--waistline", default="")
    p.add_argument("--pain-level", default="")
    p.add_argument("--sleep-quality", default="")
    p.add_argument("--skin-status", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_body_status_create)

    p = crm_sub.add_parser("product-list", help="产品/套餐列表")
    p.add_argument("--keyword", default="")
    p.add_argument("--category", default="")
    p.add_argument("--status", type=int)
    add_page(p)
    p.set_defaults(func=cmd_product_list)

    p = crm_sub.add_parser("product-create", help="创建产品/套餐")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--product-name", default="")
    p.add_argument("--product-type", default="package")
    p.add_argument("--category", default="")
    p.add_argument("--price", default="0")
    p.add_argument("--default-count", default="1")
    p.add_argument("--description", default="")
    p.set_defaults(func=cmd_product_create)

    p = crm_sub.add_parser("member-product-list", help="客户已购产品/套餐")
    p.add_argument("--member-id", default="")
    p.add_argument("--status", type=int)
    add_page(p)
    p.set_defaults(func=cmd_member_product_list)

    p = crm_sub.add_parser("product-purchase", help="客户购买产品/套餐")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--member-id", default="")
    p.add_argument("--product-id", default="")
    p.add_argument("--product-name", default="")
    p.add_argument("--total-count", default="0")
    p.add_argument("--total-amount", default="0")
    p.add_argument("--valid-start", default="")
    p.add_argument("--valid-end", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_product_purchase)

    p = crm_sub.add_parser("product-consume", help="消费客户产品/套餐")
    add_json_file(p)
    p.add_argument("--member-product-id", required=True)
    p.add_argument("--consume-count", default="1")
    p.add_argument("--consume-amount", default="0")
    p.add_argument("--visit-id", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_product_consume)

    p = crm_sub.add_parser("product-consumes", help="产品/套餐消费记录")
    p.add_argument("--member-id", default="")
    p.add_argument("--member-product-id", default="")
    add_page(p)
    p.set_defaults(func=cmd_product_consumes)

    p = crm_sub.add_parser("card-close", help="销卡")
    add_json_file(p)
    p.add_argument("--account-id", default="")
    p.add_argument("--reason", default="")
    p.add_argument("--refund-amount", default="0")
    p.add_argument("--feedback-id", default="")
    p.add_argument("--assigned-to", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_card_close)

    p = crm_sub.add_parser("card-close-list", help="销卡记录")
    p.add_argument("--member-id", default="")
    add_page(p)
    p.set_defaults(func=cmd_card_close_list)

    p = crm_sub.add_parser("suggestion-list", help="建议列表")
    p.add_argument("--status", default="")
    add_page(p)
    p.set_defaults(func=cmd_suggestion_list)

    p = crm_sub.add_parser("suggestion-create", help="创建建议")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--member-id", default="")
    p.add_argument("--feedback-id", default="")
    p.add_argument("--content", default="")
    p.add_argument("--category", default="")
    p.set_defaults(func=cmd_suggestion_create)

    p = crm_sub.add_parser("suggestion-status", help="更新建议状态")
    add_json_file(p)
    p.add_argument("--suggestion-id", required=True)
    p.add_argument("--status", required=True, choices=["pending", "adopted", "rejected", "duplicate", "implemented"])
    p.add_argument("--notes", default="")
    p.add_argument("--rejected-reason", default="")
    p.set_defaults(func=cmd_suggestion_status)

    p = crm_sub.add_parser("issue-list", help="问题列表")
    p.add_argument("--status", default="")
    add_page(p)
    p.set_defaults(func=cmd_issue_list)

    p = crm_sub.add_parser("issue-create", help="创建问题")
    add_json_file(p)
    p.add_argument("--store-id", default="")
    p.add_argument("--member-id", default="")
    p.add_argument("--feedback-id", default="")
    p.add_argument("--card-close-id", default="")
    p.add_argument("--title", default="")
    p.add_argument("--description", default="")
    p.add_argument("--severity", default="medium")
    p.add_argument("--category", default="")
    p.add_argument("--assigned-to", default="")
    p.add_argument("--fix-plan", default="")
    p.add_argument("--fix-deadline", default="")
    p.set_defaults(func=cmd_issue_create)

    p = crm_sub.add_parser("issue-update", help="更新问题")
    add_json_file(p)
    p.add_argument("--issue-id", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--description", default="")
    p.add_argument("--severity", default="")
    p.add_argument("--category", default="")
    p.add_argument("--status", default="")
    p.add_argument("--assigned-to", default="")
    p.add_argument("--fix-plan", default="")
    p.add_argument("--fix-result", default="")
    p.set_defaults(func=cmd_issue_update)

    p = crm_sub.add_parser("issue-fix", help="标记问题已修复")
    add_json_file(p)
    p.add_argument("--issue-id", required=True)
    p.add_argument("--plan", default="")
    p.add_argument("--result", default="")
    p.set_defaults(func=cmd_issue_fix)

    p = crm_sub.add_parser("issue-close", help="关闭问题")
    add_json_file(p)
    p.add_argument("--issue-id", required=True)
    p.add_argument("--result", default="")
    p.set_defaults(func=cmd_issue_close)

    p = crm_sub.add_parser("feedback-bind", help="绑定反馈到客户/到店/销卡")
    add_json_file(p)
    p.add_argument("--feedback-id", required=True)
    p.add_argument("--member-id", default="")
    p.add_argument("--visit-id", default="")
    p.add_argument("--card-close-id", default="")
    p.set_defaults(func=cmd_feedback_bind)

    feedback = sub.add_parser("feedback", help="反馈命令")
    feedback_sub = feedback.add_subparsers(dest="feedback_command", required=True)

    p = feedback_sub.add_parser("record-list", help="反馈记录列表")
    p.add_argument("--store-id", default="")
    p.add_argument("--employee-id", default="")
    p.add_argument("--satisfaction", default="")
    p.add_argument("--start-date", default="")
    p.add_argument("--end-date", default="")
    add_page(p)
    p.set_defaults(func=cmd_record_list)

    p = feedback_sub.add_parser("process", help="提交文本模拟客户反馈处理（会调用 LLM）")
    add_json_file(p)
    p.add_argument("--store-name", required=False, default="")
    p.add_argument("--employee-number", required=False, default="")
    p.add_argument("--text", required=False, default="")
    p.add_argument("--session-id", default="")
    p.add_argument("--device-mac", default="")
    p.add_argument("--satisfaction", default="")
    p.add_argument("--store-id", default="")
    p.add_argument("--employee-id", default="")
    p.set_defaults(func=cmd_feedback_process)

    admin = sub.add_parser("admin", help="门店/员工管理查询")
    admin_sub = admin.add_subparsers(dest="admin_command", required=True)

    p = admin_sub.add_parser("store-list", help="门店列表")
    p.add_argument("--keyword", default="")
    add_page(p)
    p.set_defaults(func=cmd_store_list)

    p = admin_sub.add_parser("employee-list", help="员工列表")
    p.add_argument("--store-id", default="")
    add_page(p)
    p.set_defaults(func=cmd_employee_list)

    stats = sub.add_parser("stats", help="统计命令")
    stats_sub = stats.add_subparsers(dest="stats_command", required=True)

    p = stats_sub.add_parser("employee-kpi", help="员工 KPI")
    p.add_argument("--start-date", default="")
    p.add_argument("--end-date", default="")
    p.set_defaults(func=cmd_employee_kpi)

    p = stats_sub.add_parser("employee-records", help="员工评价明细")
    p.add_argument("--employee-id", required=True)
    p.add_argument("--group", choices=["", "good", "middle", "bad"], default="")
    add_page(p)
    p.set_defaults(func=cmd_employee_records)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
