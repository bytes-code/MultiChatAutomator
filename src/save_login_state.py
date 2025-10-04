#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatGPT登录状态保存工具

这个工具用于首次登录ChatGPT并保存登录状态，避免后续使用时被Cloudflare拦截
运行此工具后，会生成 chatgpt_session.json 文件，包含登录状态信息
"""

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth

async def save_chatgpt_login_state():
    """保存ChatGPT登录状态"""
    stealth = Stealth()
    async with async_playwright() as p:
        # 启动浏览器（必须显示，方便手动登录）
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100,
            args=[
                '--disable-dev-shm-usage', 
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # 创建上下文
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # 应用反检测
        await stealth.apply_stealth_async(page)
        
        print("🌐 正在导航到ChatGPT...")
        await page.goto("https://chatgpt.com/")
        
        await asyncio.sleep(10)

        # 保存登录状态
        session_file = "chatgpt_session.json"
        await context.storage_state(path=session_file)
        
        print(f"💾 登录状态已保存到: {session_file}")
        print("✅ 保存完成！后续使用将自动加载此登录状态")
        
        # 验证保存的状态
        import os
        if os.path.exists(session_file):
            file_size = os.path.getsize(session_file)
            print(f"📄 文件大小: {file_size} 字节")
                    
        
        await asyncio.sleep(10)
        await browser.close()

async def test_saved_login_state():
    """测试保存的登录状态是否有效"""
    import os
    session_file = "chatgpt_session.json"
    
    if not os.path.exists(session_file):
        print("❌ 未找到登录状态文件，请先运行保存登录状态")
        return False
    
    print("🧪 测试保存的登录状态...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # 使用保存的登录状态创建上下文
        context = await browser.new_context(storage_state=session_file)
        page = await context.new_page()
        
        await page.goto("https://chatgpt.com/")
        await asyncio.sleep(5)
        
        await browser.close()

async def main():
    """主函数"""
    print("ChatGPT登录状态管理工具")
    print("=" * 50)
    
    import os
    session_file = "chatgpt_session.json"
    
    # 保存新的登录状态
    await save_chatgpt_login_state()
    
    if os.path.exists(session_file):
        print(f"📁 发现已有登录状态文件: {session_file}")
        await test_saved_login_state()
        print("✅ 现有登录状态有效，无需重新登录")
    

    
if __name__ == "__main__":
    asyncio.run(main())
