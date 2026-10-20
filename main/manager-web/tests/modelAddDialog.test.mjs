import Vue from 'vue';
import { parseComponent } from 'vue-template-compiler';
import { describe, expect, it, vi } from 'vitest';
import source from '../src/components/AddModelDialog.vue?raw';

// The unit-test runner has no Vue SFC plugin. Load the real component's script
// with its API and dialog dependencies stubbed; keep Vue's reactivity.
const script = parseComponent(source).script.content
  .replace(/^import .*;$/gm, '')
  .replace('export default', 'return');
const component = new Function('CustomDialog', 'Api', script)({}, {});

function makeVm() {
  const vm = new Vue({
    ...component,
    propsData: { visible: false, modelType: 'TTS' },
  });
  vm.$message = { error: vi.fn() };
  vm.$t = (key) => key;
  vm.providerFields = [
    { label: '音量', prop: 'volume', type: 'json-textarea', placeholder: '请输入volume' },
    { label: '密钥', prop: 'api_key', type: 'password', placeholder: '请输入api_key' },
  ];
  vm.formData.supplier = 'test-provider';
  return vm;
}

function submitted(vm) {
  let captured;
  vm.$on('confirm', (data) => {
    captured = data;
  });
  vm.confirm();
  return captured;
}

describe('add dialog dict fields', () => {
  it('parses valid JSON dict input into an object before submit', () => {
    const vm = makeVm();
    vm.formData.configJson = { volume: '{"speed":1,"volume":10}', api_key: 'sk-xxx' };

    const data = submitted(vm);

    expect(data.configJson.volume).toEqual({ speed: 1, volume: 10 });
    expect(data.configJson.api_key).toBe('sk-xxx');
    expect(vm.$message.error).not.toHaveBeenCalled();
  });

  it('blocks invalid JSON input and does not emit confirm', () => {
    const vm = makeVm();
    vm.formData.configJson = { volume: '{bad json', api_key: 'sk-xxx' };

    expect(submitted(vm)).toBeUndefined();
    expect(vm.$message.error).toHaveBeenCalled();
  });

  it.each(['[1,2]', 'null', '"text"', '1'])(
    'blocks non-object JSON %s',
    (value) => {
      const vm = makeVm();
      vm.formData.configJson = { volume: value, api_key: 'sk-xxx' };

      expect(submitted(vm)).toBeUndefined();
      expect(vm.$message.error).toHaveBeenCalled();
    },
  );

  it('leaves empty strings and existing object values untouched', () => {
    const vm = makeVm();
    const obj = { speed: 2 };
    vm.formData.configJson = { volume: obj, api_key: '' };

    const data = submitted(vm);

    expect(data.configJson.volume).toBe(obj);
    expect(data.configJson.api_key).toBe('');
    expect(vm.$message.error).not.toHaveBeenCalled();
  });
});
