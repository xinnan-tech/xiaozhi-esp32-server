package xiaozhi.common.xss;

import org.jsoup.Jsoup;
import org.jsoup.safety.Safelist;

/**
 * XSS过滤工具类
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class XssUtils extends Safelist {

    /**
     * XSS过滤
     */
    public static String filter(String html) {
        return Jsoup.clean(html, xssWhitelist());
    }

    /**
     * XSS过滤白名单
     */
    private static Safelist xssWhitelist() {
        return new Safelist()
                //支持的标签
                .addTags("a", "b", "blockquote", "br", "caption", "cite", "code", "col", "colgroup", "dd", "div", "dl",
                        "dt", "em", "h1", "h2", "h3", "h4", "h5", "h6", "i", "img", "li", "ol", "p", "pre", "q", "small",
                        "strike", "strong", "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
                        "embed", "object", "param", "span")

                //支持的标签属性
                .addAttributes("a", "href", "class", "style", "target", "rel", "nofollow")
                .addAttributes("blockquote", "cite")
                .addAttributes("code", "class", "style")
                .addAttributes("col", "span", "width")
                .addAttributes("colgroup", "span", "width")
                .addAttributes("img", "align", "alt", "height", "src", "title", "width", "class", "style")
                .addAttributes("ol", "start", "type")
                .addAttributes("q", "cite")
                .addAttributes("table", "summary", "width", "class", "style")
                .addAttributes("tr", "abbr", "axis", "colspan", "rowspan", "width", "style")
                .addAttributes("td", "abbr", "axis", "colspan", "rowspan", "width", "style")
                .addAttributes("th", "abbr", "axis", "colspan", "rowspan", "scope", "width", "style")
                .addAttributes("ul", "type", "style")
                .addAttributes("pre", "class", "style")
                .addAttributes("div", "class", "id", "style")
                .addAttributes("embed", "src", "wmode", "flashvars", "pluginspage", "allowFullScreen", "allowfullscreen",
                        "quality", "width", "height", "align", "allowScriptAccess", "allowscriptaccess", "allownetworking", "type")
                .addAttributes("object", "type", "id", "name", "data", "width", "height", "style", "classid", "codebase")
                .addAttributes("param", "name", "value")
                .addAttributes("span", "class", "style")

                //标签属性对应的协议
                .addProtocols("a", "href", "ftp", "http", "https", "mailto")
                .addProtocols("img", "src", "http", "https")
                .addProtocols("blockquote", "cite", "http", "https")
                .addProtocols("cite", "cite", "http", "https")
                .addProtocols("q", "cite", "http", "https")
                .addProtocols("embed", "src", "http", "https");
    }

}