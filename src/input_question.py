import asyncio
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth

class ChatGPTAutomation:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.stealth = Stealth()  # 实例化 Stealth 类
    
    async def start_browser(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            slow_mo=200,
            args=[
                '--disable-dev-shm-usage', 
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ],
            timeout=30000
        )
        
        # 尝试加载已保存的登录状态
        context_options = {
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 检查是否存在保存的登录状态
        import os
        session_file = "chatgpt_session.json"
        if os.path.exists(session_file):
            print("🔑 发现已保存的登录状态，正在加载...")
            context_options['storage_state'] = session_file
        else:
            print("❌ 未发现登录状态文件 chatgpt_session.json")
            print("请先运行 save_login_state.py 保存登录状态")
            raise Exception("缺少登录状态文件，请先运行 save_login_state.py")
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # 应用 stealth 异步方法
        await self.stealth.apply_stealth_async(self.page)
        
        await self.page.goto("about:blank", timeout=5000)
    
    async def send_message_and_get_response(self, question):
        """发送消息并获取回答"""
        # 导航到 ChatGPT 页面
        await self.page.goto("https://chatgpt.com/")
        
        # 等待页面加载完成
        print("🔄 使用保存的登录状态，等待页面加载...")
        await asyncio.sleep(3)
        
        # 输入框选择器
        input_selectors = [
            'textarea[placeholder*="Message ChatGPT"]',  # 最新的选择器
            'textarea[placeholder*="Message"]',          # 通用Message
            'div[contenteditable="true"][data-testid*="textbox"]',  # 新版本可能用div
            'textarea[data-id="root"]',                  # 旧版本
            '#prompt-textarea',                          # ID选择器
            'textarea[placeholder*="Send a message"]',   # 备用
            'div[contenteditable="true"]'                # 最后备用
        ]
        
        print("🔍 查找输入框...")
        input_element = None
        
        # 先快速检查一遍是否已经存在
        for selector in input_selectors:
            element = await self.page.query_selector(selector)
            if element:
                # 检查元素是否可见
                is_visible = await element.is_visible()
                if is_visible:
                    input_element = element
                    print(f"✅ 快速找到输入框: {selector}")
                    break
        
        print(f"找到输入框，开始输入问题")
        await input_element.click()
        await input_element.fill("")
        await input_element.type(question, delay=100)
        
        # 发送按钮选择器
        send_selectors = [
            '[data-testid="send-button"]',
            'button[aria-label*="Send"]',
            'button:has-text("Send")',
            'button svg[data-icon="arrow-up"]'
        ]
        
        send_button = None
        for selector in send_selectors:
            try:
                send_button = await self.page.wait_for_selector(selector, state="visible")
                break
            except:
                continue
        
        if send_button:
            await send_button.click()
        else:
            await input_element.press('Enter')
        
        # 等待回复完成 - 通过检测复制/点赞按钮来判断
        await asyncio.sleep(30)
        print("回复完成")
        # 回复内容选择器
        response_selectors = [
            '[data-message-author-role="assistant"] .markdown',
            '[data-message-author-role="assistant"] p',
            '.group .markdown p',
            '.group p',
            '[role="presentation"] p'
        ]
        
        response_text = ""
        for selector in response_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    for element in reversed(elements):
                        text = await element.inner_text()
                        if text.strip():
                            response_text = text.strip()
                            break
                    if response_text:
                        break
            except:
                continue
        
        if not response_text:
            try:
                messages = await self.page.query_selector_all('[data-testid*="conversation-turn"]')
                if messages:
                    last_message = messages[-1]
                    response_text = await last_message.inner_text()
            except:
                response_text = "无法获取回复内容"
        
        return response_text
    
    async def process_multiple_questions(self, questions):
        """批量处理多个问题"""
        results = []
        total = len(questions)
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'='*60}")
            print(f"📝 处理第 {i}/{total} 个问题")
            print(f"问题: {question}")
            
            try:
                response = await self.send_message_and_get_response(question)
                
                results.append({
                    'question_number': i,
                    'question': question,
                    'response': response,
                    'success': True
                })
                
                print(f"✅ 第 {i} 个问题处理完成")
                print(f"回答预览: {response[:100]}...")
                
            except Exception as e:
                print(f"❌ 第 {i} 个问题处理失败: {e}")
                results.append({
                    'question_number': i,
                    'question': question,
                    'response': f"处理失败: {e}",
                    'success': False
                })
            
            # 问题之间稍作间隔，避免请求过快
            if i < total:
                print("⏳ 等待3秒后处理下一个问题...")
                await asyncio.sleep(3)
        
        return results
    
    async def close(self):
        """关闭浏览器和相关资源"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def batch_ask_questions(self, questions_list):
        """
        批量提问接口
        
        Args:
            questions_list (list): 问题列表，例如：["问题1", "问题2", "问题3"]
        
        Returns:
            dict: 包含处理结果的字典
        """
        try:
            # 启动浏览器
            await self.start_browser()
            
            # 批量处理问题
            results = await self.process_multiple_questions(questions_list)
            
            # 统计结果
            successful_count = sum(1 for r in results if r['success'])
            failed_count = len(results) - successful_count
            
            return {
                "success": True,
                "total_questions": len(results),
                "successful_count": successful_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_questions": len(questions_list) if questions_list else 0,
                "successful_count": 0,
                "failed_count": len(questions_list) if questions_list else 0,
                "results": []
            }

async def chatgpt_batch_api(questions_list):
    """
    ChatGPT批量提问API接口
    
    Args:
        questions_list (list): 问题列表
        auto_close (bool): 是否自动关闭浏览器，默认True
    
    Returns:
        dict: 处理结果
    """
    chatgpt = ChatGPTAutomation()
    
    try:
        result = await chatgpt.batch_ask_questions(questions_list)
        return result
    finally:
        await chatgpt.close()

async def main():
    """使用API接口进行批量提问"""
    
    # 定义10个品牌推荐相关的SEO问题
    questions = [
        "2025年最值得购买的小米手机型号推荐有哪些？",
        "华为笔记本电脑哪款性价比最高？推荐理由是什么？",
    ]
    
    # 调用API接口
    result = await chatgpt_batch_api(questions)
    print(result)
    
    return result

if __name__ == "__main__":
    asyncio.run(main())