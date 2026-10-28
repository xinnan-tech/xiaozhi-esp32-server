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
const functionDialogSource = await readFile(
  new URL('../src/components/FunctionDialog.vue', import.meta.url),
  'utf8',
);
const modelConfigSource = await readFile(
  new URL('../src/views/ModelConfig.vue', import.meta.url),
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

test('model navigation keeps its scrollable layout declarations', () => {
  const navStyles = modelConfigSource.match(/\.nav-panel\s*\{([^}]*)\}/)?.[1];
  const itemStyles = modelConfigSource.match(
    /\.nav-panel\s+\.el-menu-item\s*\{([^}]*)\}/,
  )?.[1];

  assert.ok(navStyles, 'model navigation should define its layout');
  assert.ok(itemStyles, 'model menu items should define their layout');
  const wrapperStyles = modelConfigSource.match(/\.main-wrapper\s*\{([^}]*)\}/)?.[1];
  assert.ok(wrapperStyles, 'model page wrapper should define its height');

  assert.match(navStyles, /box-sizing:\s*border-box;/);
  assert.match(navStyles, /overflow-y:\s*auto;/);
  assert.match(navStyles, /display:\s*flex;/);
  assert.match(navStyles, /flex-direction:\s*column;/);
  assert.match(itemStyles, /flex-shrink:\s*0;/);
  assert.match(wrapperStyles, /height:\s*calc\([^)]*vh[^)]*\)/);

  // 断言只取第一条同名规则，后面再补一条就能盖掉上面三条，必须挡住
  assert.equal(
    (modelConfigSource.match(/\.nav-panel\s*\{/g) || []).length,
    1,
    'model navigation should keep a single rule',
  );
  assert.equal(
    (modelConfigSource.match(/\.nav-panel\s+\.el-menu-item\s*\{/g) || []).length,
    1,
    'model menu items should keep a single rule',
  );
  // 复合选择器特异性更高，能直接盖掉可滚属性
  assert.equal(
    (modelConfigSource.match(/\.nav-panel[.:\[#][^{}]*\{/g) || []).length,
    0,
    'model navigation should not use composite selectors',
  );

  const styleSource = modelConfigSource.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1];
  assert.ok(styleSource, 'model config should define its styles');
  const ruleSelectors = styleSource
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/[^\n]*/g, '')
    .split('}')
    .map((chunk) => {
      const open = chunk.indexOf('{');
      return open < 0 ? null : chunk.slice(0, open).trim();
    })
    .filter((selector) => selector && !selector.startsWith('@'));

  // 上面几条挡不住带伪类的后代选择器（.nav-panel .el-menu-item:hover），
  // 它特异性一样更高，照样能盖掉可滚属性，所以把 nav 相关的选择器逐条列出来核对
  assert.deepEqual(
    ruleSelectors.filter((selector) => selector.includes('.nav-panel')).sort(),
    [
      '.nav-panel',
      '.nav-panel .el-menu-item',
      '.nav-panel .el-menu-item.is-active',
      '.nav-panel .el-menu-item.is-active::before',
      '::v-deep .nav-panel .el-menu-item.is-active .menu-text',
    ].sort(),
    'model navigation should keep its declared rules',
  );
  assert.deepEqual(
    ruleSelectors.filter((selector) => selector.includes('.main-wrapper')),
    ['.main-wrapper'],
    'model page wrapper should keep a single rule',
  );
});

test('function dialog footer stays above the expanding MCP tools section', () => {
  const mcpLayer = functionDialogSource.match(
    /\.mcp-access-point\s*\{[^}]*z-index:\s*(\d+);/s,
  );
  const footerLayer = functionDialogSource.match(
    /\.drawer-footer\s*\{[^}]*z-index:\s*(\d+);/s,
  );

  assert.ok(mcpLayer, 'MCP section should define its stacking layer');
  assert.ok(footerLayer, 'drawer footer should define its stacking layer');
  assert.ok(Number(footerLayer[1]) > Number(mcpLayer[1]));
});
