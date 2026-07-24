/* eslint-disable test/no-import-node-test -- this zero-dependency gate intentionally uses Node's built-in runner */
import assert from 'node:assert/strict'
import test from 'node:test'
import { parseDeviceLastConnectedAtTimestamp } from './deviceTimeUtils.mjs'

test('parses the backend Long timestamp serialized as a string', () => {
  const timestamp = '1783689702000'
  assert.equal(parseDeviceLastConnectedAtTimestamp(timestamp)?.getTime(), Number(timestamp))
})

test('rejects missing and malformed device timestamps', () => {
  assert.equal(parseDeviceLastConnectedAtTimestamp(null), null)
  assert.equal(parseDeviceLastConnectedAtTimestamp(''), null)
  assert.equal(parseDeviceLastConnectedAtTimestamp('not-a-timestamp'), null)
})
