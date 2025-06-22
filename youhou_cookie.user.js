// ==UserScript==
// @name         抖音 Cookie & URL 获取器
// @namespace    https://github.com/lyswhut/Douyin_TikTok_Download_API/
// @version      0.5
// @description  自动监听并捕获抖音ab/params请求的完整URL和Cookie，直接在页面右下角展示并提供一键复制功能。
// @author       Gemini
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
    let isCaptured = false;

    // --- UI 元素创建 ---

    // 1. 创建固定展示容器
    const displayContainer = document.createElement('div');
    Object.assign(displayContainer.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: '9999',
        width: '380px',
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        border: '1px solid #ddd',
        borderRadius: '8px',
        boxShadow: '0 5px 15px rgba(0, 0, 0, 0.2)',
        padding: '15px',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        fontSize: '13px',
        color: '#333',
        boxSizing: 'border-box'
    });

    // 2. 创建标题
    const title = document.createElement('h4');
    title.textContent = '抖音 ab/params 捕获器';
    Object.assign(title.style, {
        marginTop: '0',
        marginBottom: '10px',
        borderBottom: '1px solid #eee',
        paddingBottom: '8px',
        fontSize: '14px',
        fontWeight: '600'
    });

    // 3. URL 展示区
    const urlLabel = document.createElement('div');
    urlLabel.textContent = '请求 URL:';
    urlLabel.style.fontWeight = '500';
    urlLabel.style.marginBottom = '4px';

    const urlDisplay = document.createElement('textarea');
    urlDisplay.readOnly = true;
    urlDisplay.textContent = '等待请求...';
    Object.assign(urlDisplay.style, {
        width: '100%',
        height: '60px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '8px',
        marginBottom: '10px',
        boxSizing: 'border-box',
        backgroundColor: '#f7f7f7',
        fontSize: '12px',
        resize: 'none',
        wordBreak: 'break-all'
    });

    // 4. Cookie 展示区
    const cookieLabel = document.createElement('div');
    cookieLabel.textContent = 'Cookie:';
    cookieLabel.style.fontWeight = '500';
    cookieLabel.style.marginBottom = '4px';

    const cookieDisplay = document.createElement('textarea');
    cookieDisplay.readOnly = true;
    cookieDisplay.textContent = '等待请求...';
    Object.assign(cookieDisplay.style, {
        width: '100%',
        height: '100px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '8px',
        marginBottom: '10px',
        boxSizing: 'border-box',
        backgroundColor: '#f7f7f7',
        fontSize: '12px',
        resize: 'none',
        wordBreak: 'break-all'
    });

    // 5. 创建复制按钮
    const copyButton = document.createElement('button');
    copyButton.textContent = '复制 Cookie';
    copyButton.disabled = true;
    Object.assign(copyButton.style, {
        width: '100%',
        padding: '10px',
        border: 'none',
        borderRadius: '5px',
        backgroundColor: '#ccc',
        color: '#666',
        cursor: 'not-allowed',
        fontSize: '14px',
        fontWeight: 'bold',
        transition: 'background-color 0.2s ease'
    });

    // 6. 组装UI并添加到页面
    displayContainer.appendChild(title);
    displayContainer.appendChild(urlLabel);
    displayContainer.appendChild(urlDisplay);
    displayContainer.appendChild(cookieLabel);
    displayContainer.appendChild(cookieDisplay);
    displayContainer.appendChild(copyButton);
    document.body.appendChild(displayContainer);


    // --- 捕获逻辑 ---
    function handleCapture(requestUrl) {
        // 避免重复捕获和更新
        if (isCaptured) return;

        const currentCookie = document.cookie;
        if (currentCookie) {
            isCaptured = true;
            const formattedCookie = `Cookie: ${currentCookie}`;

            // 更新UI
            urlDisplay.value = requestUrl;
            cookieDisplay.value = formattedCookie;

            // 激活复制按钮
            copyButton.disabled = false;
            copyButton.style.backgroundColor = '#fe2c55';
            copyButton.style.color = 'white';
            copyButton.style.cursor = 'pointer';

            // 添加悬停效果
            copyButton.onmouseover = () => { if (!copyButton.disabled) copyButton.style.backgroundColor = '#e4284d'; };
            copyButton.onmouseout = () => { if (!copyButton.disabled) copyButton.style.backgroundColor = '#fe2c55'; };

            GM_notification({
                title: '请求已捕获',
                text: '已自动捕获 URL 和 Cookie。',
                timeout: 3000
            });
        }
    }

    // --- 网络请求拦截 ---
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const request = args[0];
        const url = typeof request === 'string' ? request : request.url;
        
        if (typeof url === 'string' && url.includes(targetUrlPath)) {
            // 使用setTimeout确保浏览器有时间处理完请求附带的Set-Cookie头
            setTimeout(() => handleCapture(url), 100);
        }
        return originalFetch.apply(this, args);
    };

    const originalXhrOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        if (typeof url === 'string' && url.includes(targetUrlPath)) {
            const requestUrl = new URL(url, document.baseURI).href;
            this.addEventListener('load', () => {
                setTimeout(() => handleCapture(requestUrl), 100);
            });
        }
        return originalXhrOpen.apply(this, [method, url, ...rest]);
    };

    // --- 复制按钮事件监听 ---
    copyButton.addEventListener('click', () => {
        if (isCaptured && !copyButton.disabled) {
            GM_setClipboard(cookieDisplay.value, { type: 'text', mimetype: 'text/plain' });
            
            GM_notification({
                title: '复制成功',
                text: 'Cookie已复制到剪贴板！',
                timeout: 3000
            });
            
            // 提供视觉反馈
            const originalText = copyButton.textContent;
            copyButton.textContent = '✅ 已复制!';
            setTimeout(() => {
                copyButton.textContent = originalText;
            }, 2000);
        }
    });

})();
