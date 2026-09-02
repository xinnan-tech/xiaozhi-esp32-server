export const SNAPSHOT_SECRET_REDACTED = "__SNAPSHOT_SECRET_REDACTED__";

export function hasValidCurrentStateToken(value) {
  return typeof value === "string" && value.trim().length > 0;
}

export function redactSnapshotDisplayValue(value, redactedLabel, parentKey = "") {
  if (value === SNAPSHOT_SECRET_REDACTED || isSensitiveSnapshotKey(parentKey)) {
    return redactedLabel;
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactSnapshotDisplayValue(item, redactedLabel, parentKey));
  }
  if (isPlainObject(value)) {
    const sensitiveEntry = Object.keys(value).some((key) => {
      const normalizedKey = key.toLowerCase();
      return (normalizedKey === "key" || normalizedKey === "name")
        && typeof value[key] === "string"
        && isSensitiveSnapshotKey(value[key]);
    });
    return Object.keys(value).reduce((result, key) => {
      const semanticKey = resolveUrlSemanticKey(parentKey, key);
      if (sensitiveEntry && key.toLowerCase() === "value") {
        result[key] = redactedLabel;
      } else {
        result[key] = redactSnapshotDisplayValue(value[key], redactedLabel, semanticKey);
      }
      return result;
    }, {});
  }
  if (typeof value === "string" && isSnapshotUrlValue(parentKey, value)) {
    return redactSnapshotUrl(value, redactedLabel, parentKey);
  }
  return value;
}

export function normalizeSnapshotOrderedValue(value) {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeSnapshotOrderedValue(item));
  }
  if (isPlainObject(value)) {
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = normalizeSnapshotOrderedValue(value[key]);
      return result;
    }, {});
  }
  return value === undefined ? null : value;
}

export function isSensitiveSnapshotKey(key) {
  const normalized = String(key || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  return normalized === "authorization"
    || normalized.includes("authorization")
    || normalized.includes("authentication")
    || normalized === "auth"
    || normalized.endsWith("auth")
    || normalized === "cookie"
    || normalized === "cookie2"
    || normalized === "setcookie"
    || normalized === "setcookie2"
    || normalized.endsWith("cookie")
    || normalized === "session"
    || normalized.endsWith("session")
    || normalized.includes("sessionid")
    || normalized.includes("sessionkey")
    || normalized.includes("sessiontoken")
    || normalized.includes("sessioncookie")
    || normalized.endsWith("sessid")
    || normalized === "token"
    || normalized.endsWith("token")
    || normalized.includes("apikey")
    || normalized.includes("appkey")
    || normalized.includes("accesskey")
    || normalized.includes("subscriptionkey")
    || normalized.includes("privatekey")
    || normalized.includes("password")
    || normalized.includes("passwd")
    || normalized.includes("secret")
    || normalized.includes("credential");
}

function isSnapshotUrlValue(parentKey, value) {
  const normalizedKey = String(parentKey || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  return normalizedKey.includes("url")
    || normalizedKey.endsWith("uri")
    || normalizedKey.includes("endpoint")
    || normalizedKey.includes("webhook")
    || /^(?:[a-z][a-z0-9+.-]*:)*\/\//i.test(value);
}

function resolveUrlSemanticKey(parentKey, childKey) {
  if (isWebhookSemanticKey(childKey)) {
    return childKey;
  }
  if (isWebhookSemanticKey(parentKey)) {
    return childKey ? `${parentKey}.${childKey}` : parentKey;
  }
  return childKey;
}

function isWebhookSemanticKey(value) {
  const normalized = String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  return normalized.includes("webhook")
    || normalized === "hook"
    || normalized === "hooks"
    || normalized.endsWith("hook")
    || normalized.endsWith("hooks");
}

function redactSnapshotUrl(value, redactedLabel, parentKey) {
  const withoutCredentials = value.replace(
    /^((?:[a-z][a-z0-9+.-]*:)*\/\/)([^/?#\s]*@)/i,
    (match, prefix) => `${prefix}${redactedLabel}@`
  );
  const suffixIndex = withoutCredentials.search(/[?#]/);
  const base = suffixIndex < 0 ? withoutCredentials : withoutCredentials.slice(0, suffixIndex);
  const redactedBase = redactSnapshotCapabilityPath(base, redactedLabel, parentKey);
  return suffixIndex < 0
    ? redactedBase
    : `${redactedBase}${withoutCredentials[suffixIndex]}${redactedLabel}`;
}

function redactSnapshotCapabilityPath(value, redactedLabel, parentKey) {
  const absoluteUrl = value.match(/^((?:[a-z][a-z0-9+.-]*:)*\/\/)([^/?#]*)([^?#]*)$/i);
  if (!absoluteUrl) {
    return redactGenericCapabilityPath(value, redactedLabel, parentKey);
  }

  const [, scheme, authority, path = ""] = absoluteUrl;
  const hostWithPort = authority.slice(authority.lastIndexOf("@") + 1);
  const host = hostWithPort.replace(/:\d+$/, "").toLowerCase();
  let redactedPath = path;
  let providerMatched = false;

  if (host === "hooks.slack.com" || host === "hooks.slack-gov.com") {
    redactedPath = redactedPath.replace(
      /^(\/services\/[^/]+\/[^/]+\/)([^/]+)(.*)$/i,
      (match, prefix, secret, suffix) => `${prefix}${redactedLabel}${suffix}`
    );
    providerMatched = redactedPath !== path;
  } else if (
    host === "discord.com"
    || host.endsWith(".discord.com")
    || host === "discordapp.com"
    || host.endsWith(".discordapp.com")
  ) {
    redactedPath = redactedPath.replace(
      /^(\/api(?:\/v\d+)?\/webhooks\/[^/]+\/)([^/]+)(.*)$/i,
      (match, prefix, secret, suffix) => `${prefix}${redactedLabel}${suffix}`
    );
    providerMatched = redactedPath !== path;
  } else if (host === "api.telegram.org") {
    redactedPath = redactedPath.replace(
      /^((?:\/file)?\/bot[^/:]+:)([^/]+)(.*)$/i,
      (match, prefix, secret, suffix) => `${prefix}${redactedLabel}${suffix}`
    );
    providerMatched = redactedPath !== path;
  }

  if (!providerMatched) {
    redactedPath = redactGenericCapabilityPath(redactedPath, redactedLabel, parentKey);
  }

  return `${scheme}${authority}${redactedPath}`;
}

function redactGenericCapabilityPath(path, redactedLabel, parentKey) {
  const markerRedacted = path.replace(
    /(^|\/)(webhooks?|hooks?)(\/)(.+)$/i,
    (match, boundary, marker, separator) => `${boundary}${marker}${separator}${redactedLabel}`
  );
  if (markerRedacted !== path) {
    return markerRedacted;
  }
  if (!isWebhookSemanticKey(parentKey)) {
    return path;
  }
  return path.replace(
    /^(.*\/)([^/]+)(\/?)$/,
    (match, prefix, secret, suffix) => `${prefix}${redactedLabel}${suffix}`
  );
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
