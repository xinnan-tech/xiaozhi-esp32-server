import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const addressBookSource = await readFile(
  new URL('../src/views/AddressBookManagement.vue', import.meta.url),
  'utf8',
);
const correctWordApiSource = await readFile(
  new URL('../src/apis/module/correctWord.js', import.meta.url),
  'utf8',
);

test('address-book permission state consistently uses the target device MAC', () => {
  assert.match(
    addressBookSource,
    /:value="selectedPermissions\.includes\(device\.deviceId\)"/,
  );
  assert.match(
    addressBookSource,
    /@change="\(checked\) => handlePermissionToggle\(device\.deviceId, checked\)"/,
  );
  assert.match(
    addressBookSource,
    /this\.selectedPermissions = this\.allDevices\.map\(d => d\.deviceId\)/,
  );
  assert.match(
    addressBookSource,
    /this\.originalPermissions\.includes\(device\.deviceId\)/,
  );
  assert.doesNotMatch(
    addressBookSource,
    /selectedPermissions\.includes\(device\.id\)/,
  );
  assert.doesNotMatch(
    addressBookSource,
    /originalPermissions\.includes\(device\.id\)/,
  );
  assert.match(
    addressBookSource,
    /requestId !== this\.permissionRequestSequence/,
  );
  assert.match(
    addressBookSource,
    /this\.selectedDevice\?\.deviceId !== macAddress/,
  );
  assert.match(
    addressBookSource,
    /this\.permissionsLoading = true;\s*this\.selectedPermissions = \[\];\s*this\.originalPermissions = \[\];/,
  );
  assert.match(
    addressBookSource,
    /handleSavePermissions\(\) \{\s*if \(this\.permissionsLoading\) return;/,
  );
});

test('correct-word pagination maps the UI page size to the backend limit query', () => {
  assert.match(
    correctWordApiSource,
    /new URLSearchParams\(\{\s*page: params\.page,\s*limit: params\.pageSize\s*\}\)/,
  );
  assert.doesNotMatch(correctWordApiSource, /pageSize: params\.pageSize/);
});
