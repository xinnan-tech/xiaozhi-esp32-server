const HAVE_NO_RESULT = '暂无'
export default {
    HAVE_NO_RESULT, // 项目的配置信息
    PAGE: {
        LOGIN: '/login',
    },
    STORAGE_KEY: {
        TOKEN: 'TOKEN',
        PUBLIC_KEY: 'PUBLIC_KEY',
        USER_TYPE: 'USER_TYPE'
    },
    Lang: {
        'zh_cn': 'zh_cn', 'zh_tw': 'zh_tw', 'en': 'en'
    },
    FONT_SIZE: {
        'big': 'big',
        'normal': 'normal',
    }, // 获取map中的某key
    get(map, key) {
        return map[key] || HAVE_NO_RESULT
    }
}
