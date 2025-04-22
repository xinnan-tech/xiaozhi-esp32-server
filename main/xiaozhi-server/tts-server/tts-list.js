const ttsList = [
  { 
    name: "爽快思思/Skye",
    voice_source: "volcengine",
    voice_id: "zh_female_shuangkuaisisi_moon_bigtts", 
    languages: ["中文", "英文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Skye.mp3" 
  },
  {
    name: "温暖阿虎/Alvin",
    voice_source: "volcengine",
    voice_id: "zh_male_wennuanahu_moon_bigtts",
    languages: ["中文", "英文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Alvin.mp3"
  },
  {
    name: "少年梓辛/Brayan",
    voice_source: "volcengine",
    voice_id: "zh_male_shaonianzixin_moon_bigtts",
    languages: ["中文", "英文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Brayan.mp3"
  },
  {
    name: "かずね（和音）/Javier or Álvaro",
    voice_source: "volcengine",
    voice_id: "multi_male_jingqiangkanye_moon_bigtts",
    languages: ["日语", "西语"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Javier.wav"
  },
  {
    name: "はるこ（晴子）/Esmeralda",
    voice_source: "volcengine",
    voice_id: "multi_female_shuangkuaisisi_moon_bigtts",
    languages: ["日语", "西语"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Esmeralda.mp3"
  },
  {
    name: "あけみ（朱美）",
    voice_source: "volcengine",
    voice_id: "multi_female_gaolengyujie_moon_bigtts",
    languages: ["日语"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%9C%B1%E7%BE%8E.mp3"
  },
  {
    name: "ひろし（広志）/Roberto",
    voice_source: "volcengine",
    voice_id: "multi_male_wanqudashu_moon_bigtts",
    languages: ["日语", "西语"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Roberto.wav"
  },
  {
    name: "邻家女孩",
    voice_source: "volcengine",
    voice_id: "zh_female_linjianvhai_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%82%BB%E5%AE%B6%E5%A5%B3%E5%AD%A9.mp3"
  },
  {
    name: "渊博小叔",
    voice_source: "volcengine",
    voice_id: "zh_male_yuanboxiaoshu_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B8%8A%E5%8D%9A%E5%B0%8F%E5%8F%94.mp3"
  },
  {
    name: "阳光青年",
    voice_source: "volcengine",
    voice_id: "zh_male_yangguangqingnian_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%98%B3%E5%85%89%E9%9D%92%E5%B9%B4.mp3"
  },
  {
    name: "京腔侃爷/Harmony",
    voice_source: "volcengine",
    voice_id: "zh_male_jingqiangkanye_moon_bigtts",
    languages: ["中文", "英文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Harmony.mp3"
  },
  {
    name: "湾湾小何",
    voice_source: "volcengine",
    voice_id: "zh_female_wanwanxiaohe_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E6%B9%BE%E5%B0%8F%E4%BD%95.mp3"
  },
  {
    name: "湾区大叔",
    voice_source: "volcengine",
    voice_id: "zh_female_wanqudashu_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E5%8C%BA%E5%A4%A7%E5%8F%94.mp3"
  },
  {
    name: "呆萌川妹",
    voice_source: "volcengine",
    voice_id: "zh_female_daimengchuanmei_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%91%86%E8%90%8C%E5%B7%9D%E5%A6%B9.mp3"
  },
  {
    name: "广州德哥",
    voice_source: "volcengine",
    voice_id: "zh_male_guozhoudege_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%B9%BF%E5%B7%9E%E5%BE%B7%E5%93%A5.mp3"
  },
  {
    name: "北京小爷",
    voice_source: "volcengine",
    voice_id: "zh_male_beijingxiaoye_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%8C%97%E4%BA%AC%E5%B0%8F%E7%88%B7.mp3"
  },
  {
    name: "浩宇小哥",
    voice_source: "volcengine",
    voice_id: "zh_male_haoyuxiaoge_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B5%A9%E5%AE%87%E5%B0%8F%E5%93%A5.mp3"
  },
  {
    name: "广西远舟",
    voice_source: "volcengine",
    voice_id: "zh_male_guangxiyuanzhou_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%B9%BF%E8%A5%BF%E8%BF%9C%E8%88%9F.mp3"
  },
  {
    name: "妹坨洁儿",
    voice_source: "volcengine",
    voice_id: "zh_female_meituojieer_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%A6%B9%E5%9D%A8%E6%B4%81%E5%84%BF.mp3"
  },
  {
    name: "豫州子轩",
    voice_source: "volcengine",
    voice_id: "zh_male_yuzhouzixuan_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E8%B1%AB%E5%B7%9E%E5%AD%90%E8%BD%A9.mp3"
  },
  {
    name: "高冷御姐",
    voice_source: "volcengine",
    voice_id: "zh_female_gaolengyujie_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%AB%98%E5%86%B7%E5%BE%A1%E5%A7%90.mp3"
  },
  {
    name: "傲娇霸总",
    voice_source: "volcengine",
    voice_id: "zh_male_aojiaobazong_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%82%B2%E5%A8%87%E9%9C%B8%E6%80%BB.mp3"
  },
  {
    name: "魅力女友",
    voice_source: "volcengine",
    voice_id: "zh_female_meilinvyou_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%AD%85%E5%8A%9B%E5%A5%B3%E5%8F%8B.mp3"
  },
  {
    name: "深夜播客",
    voice_source: "volcengine",
    voice_id: "zh_male_shenyeboke_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B7%B1%E5%A4%9C%E6%92%AD%E5%AE%A2.mp3"
  },
  {
    name: "柔美女友",
    voice_source: "volcengine",
    voice_id: "zh_female_sajiaonvyou_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%9F%94%E7%BE%8E%E5%A5%B3%E5%8F%8B.mp3"
  },
  {
    name: "撒娇学妹",
    voice_source: "volcengine",
    voice_id: "zh_female_yuanqinvyou_moon_bigtts",
    languages: ["中文"],
    voice_demo: "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%92%92%E5%A8%87%E5%AD%A6%E5%A6%B9.mp3"
  },
  {
    name: "龙婉 女",
    voice_source: "dashscope",
    voice_id: "longwan",
    languages: ["中文普通话"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240830/dzkngm/龙婉.mp3"
  },
  {
    name: "龙橙 男",
    voice_source: "dashscope",
    voice_id: "longcheng",
    languages: ["中文普通话"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240830/ggjwfl/龙橙.wav"
  },
  {
    name: "龙华 女童",
    voice_source: "dashscope",
    voice_id: "longhua",
    languages: ["中文普通话"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240830/jpjtvy/龙华.wav"
  },
  {
    name: "龙小淳 女",
    voice_source: "dashscope",
    voice_id: "longxiaochun",
    languages: ["中文", "英文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/rlfvcd/龙小淳.mp3"
  },
  {
    name: "龙小夏 女",
    voice_source: "dashscope",
    voice_id: "longxiaoxia",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/wzywtu/龙小夏.mp3"
  },
  {
    name: "龙小诚 男",
    voice_source: "dashscope",
    voice_id: "longxiaocheng",
    languages: ["中文", "英文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/xrqksx/龙小诚.mp3"
  },
  {
    name: "龙小白 女",
    voice_source: "dashscope",
    voice_id: "longxiaobai",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/vusvze/龙小白.mp3"
  },
  {
    name: "龙老铁 男",
    voice_source: "dashscope",
    voice_id: "longlaotie",
    languages: ["中文东北口音"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/pfsfir/龙老铁.mp3"
  },
  {
    name: "龙书 男",
    voice_source: "dashscope",
    voice_id: "longshu",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/azcerd/龙书.mp3"
  },
  {
    name: "龙硕 男",
    voice_source: "dashscope",
    voice_id: "longshuo",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/lcykpl/龙硕.mp3"
  },
  {
    name: "龙婧 女",
    voice_source: "dashscope",
    voice_id: "longjing",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/ozkbmb/龙婧.mp3"
  },
  {
    name: "龙妙 女",
    voice_source: "dashscope",
    voice_id: "longmiao",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/zjnqis/龙妙.mp3"
  },
  {
    name: "龙悦 女",
    voice_source: "dashscope",
    voice_id: "longyue",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/nrkjqf/龙悦.mp3"
  },
  {
    name: "龙媛 女",
    voice_source: "dashscope",
    voice_id: "longyuan",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/xuboos/龙媛.mp3"
  },
  {
    name: "龙飞 男",
    voice_source: "dashscope",
    voice_id: "longfei",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/bhkjjx/龙飞.mp3"
  },
  {
    name: "龙杰力豆 男童",
    voice_source: "dashscope",
    voice_id: "longjielidou",
    languages: ["中文", "英文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/dctiyg/龙杰力豆.mp3"
  },
  {
    name: "龙彤 女童",
    voice_source: "dashscope",
    voice_id: "longtong",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/qyqmvo/龙彤.mp3"
  },
  {
    name: "龙祥 男",
    voice_source: "dashscope",
    voice_id: "longxiang",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/jybshd/龙祥.mp3"
  },
  {
    name: "Stella 女",
    voice_source: "dashscope",
    voice_id: "loongstella",
    languages: ["中文", "英文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/haffms/Stella.mp3"
  },
  {
    name: "Bella 女",
    voice_source: "dashscope",
    voice_id: "loongbella",
    languages: ["中文"],
    voice_demo: "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240624/tguine/Bella.mp3"
  }
];

module.exports = {
  ttsList
};

