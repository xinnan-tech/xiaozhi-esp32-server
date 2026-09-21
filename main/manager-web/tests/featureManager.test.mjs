import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the heavy dependencies before importing the module under test.
vi.mock('@/apis/api', () => ({
  default: {
    user: {
      getPubConfig: vi.fn(),
    },
    admin: {
      updateParam: vi.fn(),
    },
  },
}));

vi.mock('@/store', () => ({
  default: {
    commit: vi.fn(),
  },
}));

import featureManager from '../src/utils/featureManager.js';

describe('featureManager', () => {
  beforeEach(() => {
    // Reset to defaults so each test starts from a clean feature set.
    featureManager.resetToDefault();
  });

  it('module loads and exports the singleton', () => {
    expect(featureManager).toBeDefined();
    expect(typeof featureManager.getCurrentConfig).toBe('function');
  });

  it('resetToDefault populates the seven default feature flags', () => {
    const features = featureManager.getCurrentConfig();
    const keys = Object.keys(features).sort();
    expect(keys).toEqual([
      'addressBook',
      'asr',
      'knowledgeBase',
      'mcpAccessPoint',
      'vad',
      'voiceClone',
      'voiceprintRecognition',
    ]);
    // Every default feature should start disabled.
    for (const key of keys) {
      expect(features[key].enabled).toBe(false);
    }
  });

  it('setFeatureStatus returns false for an unknown feature key', () => {
    expect(featureManager.setFeatureStatus('notARealFeature', true)).toBe(false);
  });

  it('setFeatureStatus enables and disables a known feature', () => {
    expect(featureManager.setFeatureStatus('asr', true)).toBe(true);
    expect(featureManager.isFeatureEnabled('asr')).toBe(true);

    expect(featureManager.setFeatureStatus('asr', false)).toBe(true);
    expect(featureManager.isFeatureEnabled('asr')).toBe(false);
  });

  it('enableFeature / disableFeature / toggleFeature update state', () => {
    featureManager.enableFeature('voiceprintRecognition');
    expect(featureManager.getFeatureStatus('voiceprintRecognition')).toBe(true);

    featureManager.disableFeature('voiceprintRecognition');
    expect(featureManager.getFeatureStatus('voiceprintRecognition')).toBe(false);

    featureManager.toggleFeature('knowledgeBase');
    expect(featureManager.getFeatureStatus('knowledgeBase')).toBe(true);
    featureManager.toggleFeature('knowledgeBase');
    expect(featureManager.getFeatureStatus('knowledgeBase')).toBe(false);
  });

  it('getConfig returns a flat object of booleans', () => {
    const config = featureManager.getConfig();
    expect(Object.keys(config).sort()).toEqual([
      'addressBook',
      'asr',
      'knowledgeBase',
      'mcpAccessPoint',
      'vad',
      'voiceClone',
      'voiceprintRecognition',
    ]);
    for (const key of Object.keys(config)) {
      expect(typeof config[key]).toBe('boolean');
    }
  });

  it('getEnabledFeatures lists only enabled keys', () => {
    featureManager.enableFeature('asr');
    featureManager.enableFeature('vad');
    const enabled = featureManager.getEnabledFeatures().sort();
    expect(enabled).toEqual(['asr', 'vad']);
  });
});