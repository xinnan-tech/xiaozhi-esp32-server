export function hasTimestampValue(timestamp) {
  if (timestamp === null || timestamp === undefined) return false;
  return typeof timestamp !== 'string' || timestamp.trim() !== '';
}

export function parseTimestamp(timestamp) {
  if (!hasTimestampValue(timestamp)) return null;
  if (typeof timestamp !== 'number' && typeof timestamp !== 'string') return null;

  const normalizedTimestamp = typeof timestamp === 'string' ? timestamp.trim() : timestamp;
  const parsedTimestamp = Number(normalizedTimestamp);
  if (!Number.isFinite(parsedTimestamp)) return null;

  return Number.isNaN(new Date(parsedTimestamp).getTime()) ? null : parsedTimestamp;
}

export function parseLegacyDate(dateValue) {
  if (!dateValue) return null;
  const timestamp = new Date(dateValue).getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
}

export function formatTimestamp(timestamp, formatter = value => new Date(value).toLocaleString()) {
  const parsedTimestamp = parseTimestamp(timestamp);
  return parsedTimestamp === null ? '-' : formatter(parsedTimestamp);
}

export function formatCreateDate(timestamp, legacyDate, formatter) {
  if (!hasTimestampValue(timestamp)) return legacyDate || '-';
  return formatTimestamp(timestamp, formatter);
}

export function compareTimestamps(firstTimestamp, secondTimestamp) {
  const firstIsValid = Number.isFinite(firstTimestamp);
  const secondIsValid = Number.isFinite(secondTimestamp);

  if (firstIsValid && secondIsValid) return firstTimestamp - secondTimestamp;
  if (firstIsValid) return -1;
  if (secondIsValid) return 1;
  return 0;
}
