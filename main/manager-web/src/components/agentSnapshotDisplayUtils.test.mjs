/* eslint-disable test/no-import-node-test -- zero-dependency security regression gate */
import assert from "node:assert/strict";
import test from "node:test";
import {
  hasValidCurrentStateToken,
  normalizeSnapshotOrderedValue,
  redactSnapshotDisplayValue,
  SNAPSHOT_SECRET_REDACTED
} from "./agentSnapshotDisplayUtils.mjs";

test("accepts only non-empty opaque current-state tokens", () => {
  assert.equal(hasValidCurrentStateToken("state-token"), true);
  assert.equal(hasValidCurrentStateToken("  state-token  "), true);
  assert.equal(hasValidCurrentStateToken(""), false);
  assert.equal(hasValidCurrentStateToken("   "), false);
  assert.equal(hasValidCurrentStateToken(null), false);
  assert.equal(hasValidCurrentStateToken(123), false);
});

test("redacts nested credentials without hiding non-sensitive display values", () => {
  const redacted = redactSnapshotDisplayValue({
    apiKey: "api-secret",
    headers: [
      { key: "Authorization", value: "Bearer secret" },
      { key: "Proxy-Authorization", value: "Basic secret" },
      { key: "Set-Cookie", value: "session=secret" },
      { key: "Content-Type", value: "application/json" }
    ],
    marker: SNAPSHOT_SECRET_REDACTED,
    session_id: "session-secret",
    url: "https://user:pass@example.com/context?access_token=secret#fragment",
    visible: "kept"
  }, "[hidden]");

  assert.deepEqual(redacted, {
    apiKey: "[hidden]",
    headers: [
      { key: "Authorization", value: "[hidden]" },
      { key: "Proxy-Authorization", value: "[hidden]" },
      { key: "Set-Cookie", value: "[hidden]" },
      { key: "Content-Type", value: "application/json" }
    ],
    marker: "[hidden]",
    session_id: "[hidden]",
    url: "https://[hidden]@example.com/context?[hidden]",
    visible: "kept"
  });
});

test("uses a function parameter key when redacting scalar plugin values", () => {
  assert.equal(redactSnapshotDisplayValue("secret", "[hidden]", "clientSecret"), "[hidden]");
  assert.equal(redactSnapshotDisplayValue("secret", "[hidden]", "Ocp-Apim-Subscription-Key"), "[hidden]");
  assert.equal(redactSnapshotDisplayValue("public", "[hidden]", "clientId"), "public");
});

test("redacts mixed-case name/value credential entries", () => {
  assert.deepEqual(redactSnapshotDisplayValue({
    headers: [
      { NAME: "Authorization", VALUE: "Bearer live-secret" },
      { NaMe: "Content-Type", VaLuE: "application/json" }
    ]
  }, "[hidden]"), {
    headers: [
      { NAME: "Authorization", VALUE: "[hidden]" },
      { NaMe: "Content-Type", VaLuE: "application/json" }
    ]
  });
});

test("redacts capability URL path secrets while preserving public route identity", () => {
  const redacted = redactSnapshotDisplayValue({
    slackUrl: "https://hooks.slack.com/services/T00000000/B00000000/slack-secret",
    slackGovUrl: "https://hooks.slack-gov.com/services/T00000000/B00000000/slack-gov-secret",
    discordEndpoint: "https://discord.com/api/webhooks/123456789/discord-secret",
    telegramUri: "https://api.telegram.org/bot123456789:telegram-secret/sendMessage",
    telegramFileUri: "https://api.telegram.org/file/bot123456789:telegram-file-secret/documents/file.txt",
    callbackUrl: "https://events.example.com/api/webhook/generic-secret/delivery",
    hooksEndpoint: "https://events.example.com/v1/hooks/hook-secret/status",
    hookEndpoint: "https://events.example.com/v1/hook/singular-secret/status",
    webhooksEndpoint: "https://events.example.com/v1/webhooks/plural-secret/status",
    relativeUrl: "/api/webhooks/relative-secret/continuation",
    nested: {
      deliveryWebhook: {
        options: {
          target: "https://events.example.com/incoming/nested-secret",
          relativeTarget: "/incoming/nested-relative-secret"
        }
      }
    },
    protocolRelativeUrl: "//protocol-user:protocol-pass@example.com/context",
    jdbcUrl: "jdbc:mysql://jdbc-user:jdbc-pass@example.com/database",
    webhook: "https://capability.example.com/public-prefix/key-secret",
    restUrl: "https://api.example.com/v1/users/customer-123",
    similarMarkerUrl: "https://api.example.com/v1/webhook-settings/public-value"
  }, "[hidden]");

  assert.deepEqual(redacted, {
    slackUrl: "https://hooks.slack.com/services/T00000000/B00000000/[hidden]",
    slackGovUrl: "https://hooks.slack-gov.com/services/T00000000/B00000000/[hidden]",
    discordEndpoint: "https://discord.com/api/webhooks/123456789/[hidden]",
    telegramUri: "https://api.telegram.org/bot123456789:[hidden]/sendMessage",
    telegramFileUri: "https://api.telegram.org/file/bot123456789:[hidden]/documents/file.txt",
    callbackUrl: "https://events.example.com/api/webhook/[hidden]",
    hooksEndpoint: "https://events.example.com/v1/hooks/[hidden]",
    hookEndpoint: "https://events.example.com/v1/hook/[hidden]",
    webhooksEndpoint: "https://events.example.com/v1/webhooks/[hidden]",
    relativeUrl: "/api/webhooks/[hidden]",
    nested: {
      deliveryWebhook: {
        options: {
          target: "https://events.example.com/incoming/[hidden]",
          relativeTarget: "/incoming/[hidden]"
        }
      }
    },
    protocolRelativeUrl: "//[hidden]@example.com/context",
    jdbcUrl: "jdbc:mysql://[hidden]@example.com/database",
    webhook: "https://capability.example.com/public-prefix/[hidden]",
    restUrl: "https://api.example.com/v1/users/customer-123",
    similarMarkerUrl: "https://api.example.com/v1/webhook-settings/public-value"
  });
  assert.equal(JSON.stringify(redacted).includes("slack-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("slack-gov-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("discord-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("telegram-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("telegram-file-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("generic-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("hook-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("singular-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("plural-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("relative-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("nested-secret"), false);
  assert.equal(JSON.stringify(redacted).includes("key-secret"), false);
});

test("normalizes object keys without erasing ordered-list changes", () => {
  const before = [
    { url: "https://first.example", headers: { Zeta: "2", Accept: "json" } },
    { url: "https://second.example" }
  ];
  const sameOrder = [
    { headers: { Accept: "json", Zeta: "2" }, url: "https://first.example" },
    { url: "https://second.example" }
  ];
  const reversed = [...sameOrder].reverse();

  assert.deepEqual(
    normalizeSnapshotOrderedValue(before),
    normalizeSnapshotOrderedValue(sameOrder)
  );
  assert.notDeepEqual(
    normalizeSnapshotOrderedValue(before),
    normalizeSnapshotOrderedValue(reversed)
  );
});
