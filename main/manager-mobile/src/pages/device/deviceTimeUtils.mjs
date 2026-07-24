/** @param {unknown} timestamp */
export function parseDeviceLastConnectedAtTimestamp(timestamp) {
  if (typeof timestamp !== 'string' || !timestamp.trim()) {
    return null
  }

  const milliseconds = Number(timestamp)
  if (!Number.isFinite(milliseconds)) {
    return null
  }

  const date = new Date(milliseconds)
  return Number.isNaN(date.getTime()) ? null : date
}
