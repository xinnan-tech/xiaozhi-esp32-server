import Vue from 'vue';
import VueI18n from 'vue-i18n';
import zhCN from './zh_CN';
import zhTW from './zh_TW';
import en from './en';

Vue.use(VueI18n);

// 从本地存储获取语言设置，如果没有则使用浏览器语言或默认语言
const getDefaultLanguage = () => {
  const savedLang = localStorage.getItem('userLanguage');
  if (savedLang) {
    return savedLang;
  }
  const browserLang = navigator.language || navigator.userLanguage;
  if (browserLang.indexOf('zh') === 0) {
    if (browserLang === 'zh-TW' || browserLang === 'zh-HK' || browserLang === 'zh-MO') {
      return 'zh_TW';
    }
    return 'zh_CN';
  }
  return 'en';
};

const i18n = new VueI18n({
  locale: getDefaultLanguage(),
  fallbackLocale: 'zh_CN',
  messages: {
    'zh_CN': zhCN,
    'zh_TW': zhTW,
    'en': en
  }
});

export default i18n;

// 提供一个方法来切换语言
export const changeLanguage = (lang) => {
  i18n.locale = lang;
  localStorage.setItem('userLanguage', lang);
  // 通知组件语言已更改
  Vue.prototype.$eventBus.$emit('languageChanged', lang);
};