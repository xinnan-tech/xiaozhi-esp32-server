#!/usr/bin/env bash
# 检查那几个要连 MySQL 和 Redis 的集成测试是不是真的跑了。
# 守卫要是哪天手滑把它们全跳过了，CI 必须红，不能安安静静少跑一半门禁。
set -uo pipefail

REPORT_DIR="${1:-target/surefire-reports}"

WATCHED=(
  "xiaozhi.modules.device.DeviceTest"
  "xiaozhi.modules.model.service.impl.ModelConfigPersistenceTest"
  "xiaozhi.modules.sys.loginControllerTest"
)

if [ ! -d "$REPORT_DIR" ]; then
  echo "找不到测试报告目录：$REPORT_DIR"
  exit 1
fi

missing=()
for class in "${WATCHED[@]}"; do
  count=0
  for report in "$REPORT_DIR"/TEST-*.xml; do
    [ -e "$report" ] || continue
    name=$(sed -n 's/.*<testsuite[^>]*name="\([^"]*\)".*/\1/p' "$report" | head -1)
    if [ "$name" = "$class" ]; then
      count=$(sed -n 's/.*<testsuite[^>]*tests="\([0-9]*\)".*/\1/p' "$report" | head -1)
      count=${count:-0}
      break
    fi
  done
  if [ "$count" -eq 0 ]; then
    missing+=("$class")
  else
    echo "OK  $class 跑了 $count 条"
  fi
done

if [ ${#missing[@]} -ne 0 ]; then
  echo "这几个集成测试一条都没跑：${missing[*]}"
  echo "守卫把门禁掏空了，构建必须失败"
  exit 1
fi

echo "集成测试都跑过了"
