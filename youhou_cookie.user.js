// ==UserScript==
// @name         抖音 ttwid 直连获取器
// @namespace    https://github.com/lyswhut/Douyin_TikTok_Download_API/
// @version      0.8
// @description  静默监听抖音网络请求，自动捕获ttwid并复制到剪贴板，如果无法自动获取则提示手动操作。
// @author       Gemini & Lys
// @match        *://*.douyin.com/*
// @match        *://*.douying.com/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=douyin.com
// @grant        GM_setClipboard
// @grant        GM_notification
// @license      MIT
// ==/UserScript==

(function() {
    'use strict';

    const targetUrlPath = '/aweme/v1/web/ab/params';
    let hasAttempted = false; // 标记是否已经尝试过捕获，防止重复通知

    function handleCapture(requestUrl) {
        if (hasAttempted) return;

        // 尝试从 document.cookie 中获取 ttwid
        const ttwidMatch = document.cookie.match(/ttwid=([^;]+)/);

        if (ttwidMatch && ttwidMatch[1]) {
            hasAttempted = true;
            const ttwidValue = ttwidMatch[1];

            // 自动复制到剪贴板
            GM_setClipboard(ttwidValue, { type: 'text', mimetype: 'text/plain' });

            // 显示成功通知
            GM_notification({
                title: '抖音 ttwid 已捕获',
                text: `已自动复制到剪贴板: ${ttwidValue}`,
                timeout: 5000
            });
            console.log(`[抖音ttwid获取器] 成功捕获并复制ttwid: ${ttwidValue} from URL: ${requestUrl}`);

        } else {
            hasAttempted = true;
            // 无法自动获取，提示用户手动操作
            GM_notification({
                title: '抖音 ttwid 获取失败',
                text: '无法自动捕获 ttwid (可能是HttpOnly)。请按F12在开发者工具中手动复制。',
                timeout: 8000
            });
            console.log(`[抖音ttwid获取器] 拦截到目标请求，但无法从 document.cookie 读取 ttwid，请手动获取。URL: ${requestUrl}`);
        }
    }

    // --- 网络请求拦截 ---

    // 拦截 fetch API
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const request = args[0];
        const url = typeof request === 'string' ? request : request.url;

        if (typeof url === 'string' && url.includes(targetUrlPath)) {
            // 使用 setTimeout 确保浏览器有时间处理 Set-Cookie 头
            setTimeout(() => handleCapture(url), 500);
        }
        return originalFetch.apply(this, args);
    };

    // 拦截 XMLHttpRequest
    const originalXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        if (typeof url === 'string' && url.includes(targetUrlPath)) {
            const requestUrl = new URL(url, document.baseURI).href;
            this.addEventListener('load', () => {
                // 使用 setTimeout 确保浏览器有时间处理 Set-Cookie 头
                setTimeout(() => handleCapture(requestUrl), 500);
            });
        }
        return originalXhrOpen.apply(this, [method, url, ...rest]);
    };

    console.log('[抖音ttwid获取器] 脚本已加载，正在监听网络请求...');
})();
