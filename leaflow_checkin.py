#!/usr/bin/env python3
"""
Leaflow 多账号自动签到脚本
变量名：LEAFLOW_ACCOUNTS
变量值：邮箱1:密码1,邮箱2:密码2,邮箱3:密码3
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeaflowAutoCheckin:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        if not self.email or not self.password:
            raise ValueError("邮箱和密码不能为空")
        
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """设置Chrome驱动选项"""
        chrome_options = Options()
        
        # GitHub Actions环境配置
        if os.getenv('GITHUB_ACTIONS'):
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-software-rasterizer')
        
        # 通用配置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 页面加载优化
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-accelerated-2d-canvas')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--no-zygote')
        
        # 添加用户代理，模拟真实浏览器
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 设置页面加载策略为normal，避免timeout问题
        chrome_options.page_load_strategy = 'normal'
        
        # 添加性能优化参数
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def close_popup(self):
        """关闭初始弹窗"""
        try:
            logger.info("尝试关闭初始弹窗...")
            time.sleep(3)  # 等待弹窗加载
            
            # 尝试多种方式关闭弹窗
            try:
                # 方法1: 使用键盘ESC键
                from selenium.webdriver.common.keys import Keys
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE).perform()
                logger.info("尝试使用ESC键关闭弹窗")
                time.sleep(2)
            except:
                pass
            
            # 方法2: 点击页面特定位置
            try:
                actions = ActionChains(self.driver)
                actions.move_by_offset(10, 10).click().perform()
                logger.info("尝试点击页面关闭弹窗")
                time.sleep(2)
            except:
                pass
            
            return True
            
        except Exception as e:
            logger.warning(f"关闭弹窗时出错: {e}")
            return False
    
    def wait_for_element_clickable(self, by, value, timeout=10):
        """等待元素可点击"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    
    def wait_for_element_present(self, by, value, timeout=10):
        """等待元素出现"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    
    def login(self):
        """执行登录流程"""
        logger.info(f"开始登录流程")
        
        # 访问登录页面
        self.driver.get("https://leaflow.net/login")
        time.sleep(5)
        
        # 关闭弹窗
        self.close_popup()
        
        # 输入邮箱
        try:
            logger.info("查找邮箱输入框...")
            
            # 等待页面稳定
            time.sleep(3)
            
            # 尝试多种选择器找到邮箱输入框
            email_selectors = [
                "input[type='text']",
                "input[type='email']", 
                "input[placeholder*='邮箱']",
                "input[placeholder*='邮件']",
                "input[placeholder*='email']",
                "input[placeholder*='Email']",
                "input[name='email']",
                "input[name='username']",
                "input[id*='email']",
                "input[id*='username']",
                "#email",
                "#username"
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            email_input = element
                            logger.info(f"找到邮箱输入框: {selector}")
                            break
                    if email_input:
                        break
                except:
                    continue
            
            if not email_input:
                # 尝试使用XPath
                xpath_selectors = [
                    "//input[@type='text']",
                    "//input[@type='email']",
                    "//input[contains(@placeholder, '邮箱')]",
                    "//input[contains(@placeholder, 'email')]"
                ]
                for xpath in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                email_input = element
                                logger.info(f"通过XPath找到邮箱输入框")
                                break
                        if email_input:
                            break
                    except:
                        continue
            
            if not email_input:
                raise Exception("找不到邮箱输入框")
            
            # 清除并输入邮箱
            email_input.clear()
            email_input.send_keys(self.email)
            logger.info("邮箱输入完成")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"输入邮箱时出错: {e}")
            # 尝试使用JavaScript直接设置值
            try:
                self.driver.execute_script(f"""
                    var inputs = document.querySelectorAll('input[type="text"], input[type="email"]');
                    for(var i=0; i<inputs.length; i++) {{
                        if(inputs[i].offsetWidth > 0 && inputs[i].offsetHeight > 0) {{
                            inputs[i].value = '{self.email}';
                            break;
                        }}
                    }}
                """)
                logger.info("通过JavaScript设置邮箱")
                time.sleep(2)
            except:
                raise Exception(f"无法输入邮箱: {e}")
        
        # 输入密码
        try:
            logger.info("查找密码输入框...")
            
            password_selectors = [
                "input[type='password']",
                "input[placeholder*='密码']",
                "input[placeholder*='password']",
                "input[placeholder*='Password']",
                "input[name='password']",
                "input[id*='password']",
                "#password"
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            password_input = element
                            logger.info(f"找到密码输入框: {selector}")
                            break
                    if password_input:
                        break
                except:
                    continue
            
            if not password_input:
                # 尝试XPath
                xpath_selectors = [
                    "//input[@type='password']",
                    "//input[contains(@placeholder, '密码')]",
                    "//input[contains(@placeholder, 'password')]"
                ]
                for xpath in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                password_input = element
                                logger.info("通过XPath找到密码输入框")
                                break
                        if password_input:
                            break
                    except:
                        continue
            
            if not password_input:
                raise Exception("找不到密码输入框")
            
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("密码输入完成")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"输入密码时出错: {e}")
            # 尝试使用JavaScript
            try:
                self.driver.execute_script(f"""
                    var inputs = document.querySelectorAll('input[type="password"]');
                    for(var i=0; i<inputs.length; i++) {{
                        if(inputs[i].offsetWidth > 0 && inputs[i].offsetHeight > 0) {{
                            inputs[i].value = '{self.password}';
                            break;
                        }}
                    }}
                """)
                logger.info("通过JavaScript设置密码")
                time.sleep(2)
            except:
                raise Exception(f"无法输入密码: {e}")
        
        # 点击登录按钮
        try:
            logger.info("查找登录按钮...")
            
            # 尝试多种方式找到登录按钮
            login_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "//button[contains(text(), '登录')]",
                "//button[contains(text(), 'Login')]",
                "//button[@type='submit']",
                "//input[@type='submit']",
                "button.btn-primary",
                "button.btn-login"
            ]
            
            login_btn = None
            for selector in login_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            login_btn = element
                            logger.info(f"找到登录按钮: {selector}")
                            break
                    if login_btn:
                        break
                except:
                    continue
            
            if not login_btn:
                raise Exception("找不到登录按钮")
            
            # 点击登录按钮
            try:
                login_btn.click()
            except:
                # 如果普通点击失败，尝试使用JavaScript点击
                self.driver.execute_script("arguments[0].click();", login_btn)
            
            logger.info("已点击登录按钮")
            
        except Exception as e:
            logger.error(f"点击登录按钮失败: {e}")
            # 尝试通过表单提交
            try:
                self.driver.execute_script("document.querySelector('form').submit();")
                logger.info("通过JavaScript提交表单")
            except:
                raise Exception(f"无法提交登录表单: {e}")
        
        # 等待登录完成 - 改进的验证逻辑
        try:
            logger.info("等待登录完成...")
            
            # 等待最多30秒，检查多个成功指标
            WebDriverWait(self.driver, 30).until(
                lambda driver: any([
                    "dashboard" in driver.current_url,
                    "workspaces" in driver.current_url,
                    "/dashboard" in driver.current_url,
                    "/workspaces" in driver.current_url,
                    driver.execute_script("return document.body.innerText;").find("资源使用趋势") != -1,  # 根据你提供的成功页面内容
                    driver.execute_script("return document.body.innerText;").find("Dashboard") != -1,
                    driver.execute_script("return document.body.innerText;").find("仪表板") != -1,
                    "login" not in driver.current_url and "signin" not in driver.current_url
                ])
            )
            
            # 额外等待页面完全加载
            time.sleep(5)
            
            # 检查是否真的登录成功
            current_url = self.driver.current_url
            page_content = self.driver.page_source
            
            # 根据你提供的成功页面内容进行检查
            if "资源使用趋势" in page_content or "Dashboard" in page_content or "仪表板" in page_content:
                logger.info(f"登录成功，检测到成功页面内容")
                logger.info(f"当前URL: {current_url}")
                return True
            
            # 检查是否还在登录页面
            if "login" in current_url or "signin" in current_url:
                # 检查是否有错误消息
                error_indicators = [
                    "error", "Error", "ERROR",
                    "invalid", "Invalid", "INVALID",
                    "incorrect", "Incorrect", "INCORRECT",
                    "失败", "错误", "不正确"
                ]
                
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                for indicator in error_indicators:
                    if indicator in page_text:
                        # 提取错误信息
                        lines = page_text.split('\n')
                        for line in lines:
                            if indicator in line:
                                raise Exception(f"登录失败: {line.strip()}")
                
                raise Exception("登录后仍然在登录页面，但没有明确的错误信息")
            
            # 如果既不是明显的成功也不是失败，也认为是成功
            logger.info(f"登录可能成功，当前URL: {current_url}")
            return True
                
        except TimeoutException:
            # 检查是否有错误消息
            try:
                error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, .text-red, [class*='error'], [class*='danger']")
                for element in error_elements:
                    if element.is_displayed():
                        error_text = element.text.strip()
                        if error_text:
                            raise Exception(f"登录失败: {error_text}")
                
                # 检查页面文本中的错误关键词
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                error_keywords = ["error", "Error", "invalid", "Invalid", "incorrect", "Incorrect", "失败", "错误"]
                for keyword in error_keywords:
                    if keyword in page_text:
                        lines = page_text.split('\n')
                        for line in lines:
                            if keyword in line:
                                raise Exception(f"登录失败: {line.strip()}")
                
                raise Exception("登录超时，无法确认登录状态")
            except Exception as e:
                if "登录失败" in str(e):
                    raise e
                else:
                    raise Exception(f"登录超时: {str(e)}")
    
    def get_balance(self):
        """获取当前账号的总余额"""
        try:
            logger.info("获取账号余额...")
            
            # 跳转到仪表板页面
            self.driver.get("https://leaflow.net/dashboard")
            time.sleep(3)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 尝试多种选择器查找余额元素
            balance_selectors = [
                "//*[contains(text(), '¥') or contains(text(), '￥') or contains(text(), '元')]",
                "//*[contains(@class, 'balance')]",
                "//*[contains(@class, 'money')]",
                "//*[contains(@class, 'amount')]",
                "//button[contains(@class, 'dollar')]",
                "//span[contains(@class, 'font-medium')]",
                "//div[contains(@class, 'balance')]",
                "//div[contains(text(), '¥')]",
                "//span[contains(text(), '¥')]"
            ]
            
            for selector in balance_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # 查找包含数字和货币符号的文本
                        if any(char.isdigit() for char in text) and ('¥' in text or '￥' in text or '元' in text or '￥' in text or '$' in text):
                            # 提取数字部分
                            import re
                            numbers = re.findall(r'\d+\.?\d*', text)
                            if numbers:
                                balance = numbers[0]
                                logger.info(f"找到余额: {balance}元")
                                return f"{balance}元"
                except:
                    continue
            
            logger.warning("未找到余额信息")
            return "未知"
            
        except Exception as e:
            logger.warning(f"获取余额时出错: {e}")
            return "未知"
    
    def wait_for_checkin_page_loaded(self, max_retries=3, wait_time=20):
        """等待签到页面完全加载，支持重试"""
        for attempt in range(max_retries):
            logger.info(f"等待签到页面加载，尝试 {attempt + 1}/{max_retries}，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            
            try:
                # 根据你提供的签到页面特征进行检查
                checkin_indicators = [
                    "//a[contains(@class, 'navbar-brand') and contains(., '每日签到')]",
                    "//h1[contains(@class, 'page-header') and contains(., '每日签到')]",
                    "//i[contains(@class, 'bi-calendar-check')]",
                    "//*[contains(text(), '每日签到')]",
                    "//button[contains(text(), '立即签到')]",
                    "//button[contains(text(), '已签到')]"
                ]
                
                for indicator in checkin_indicators:
                    try:
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, indicator))
                        )
                        
                        if element.is_displayed():
                            logger.info(f"找到签到页面元素: {indicator}")
                            return True
                    except:
                        continue
                
                logger.warning(f"第 {attempt + 1} 次尝试未找到签到页面特征，继续等待...")
                
            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次检查签到页面时出错: {e}")
        
        return False
    
    def find_and_click_checkin_button(self):
        """查找并点击签到按钮 - 处理已签到状态"""
        logger.info("查找签到按钮...")
        
        try:
            # 先等待页面可能的重载
            time.sleep(5)
            
            # 尝试多种选择器找到签到按钮
            checkin_selectors = [
                "//button[contains(text(), '立即签到')]",
                "//button[contains(text(), '签到')]",
                "//input[@value='签到']",
                "//button[@type='submit']",
                "//button[contains(@class, 'btn-success')]",
                "//button[contains(@class, 'btn-primary')]",
                "//a[contains(@class, 'btn') and contains(text(), '签到')]"
            ]
            
            for selector in checkin_selectors:
                try:
                    checkin_btn = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    
                    if checkin_btn.is_displayed():
                        # 检查按钮文本，如果包含"已签到"则说明今天已经签到过了
                        btn_text = checkin_btn.text.strip()
                        if "已签到" in btn_text or "已签" in btn_text or "签到过" in btn_text:
                            logger.info("伙计，今日你已经签到过了！")
                            return "already_checked_in"
                        
                        # 检查按钮是否可用
                        if checkin_btn.is_enabled():
                            logger.info(f"找到并点击立即签到按钮: {btn_text}")
                            # 使用JavaScript点击确保可靠性
                            self.driver.execute_script("arguments[0].click();", checkin_btn)
                            time.sleep(2)
                            return True
                        else:
                            logger.info("签到按钮不可用，可能已经签到过了")
                            return "already_checked_in"
                        
                except Exception as e:
                    logger.debug(f"选择器未找到按钮: {selector} - {e}")
                    continue
            
            logger.error("找不到签到按钮")
            return False
                    
        except Exception as e:
            logger.error(f"查找签到按钮时出错: {e}")
            return False
    
    def checkin(self):
        """执行签到流程"""
        logger.info("跳转到签到页面...")
        
        try:
            # 使用正确的签到页面地址
            checkin_url = "https://checkin.leaflow.net/"
            logger.info(f"访问签到页面: {checkin_url}")
            
            # 设置页面加载超时为60秒
            self.driver.set_page_load_timeout(60)
            
            # 跳转到签到页面
            self.driver.get(checkin_url)
            
        except TimeoutException:
            logger.warning("页面加载超时，但可能已部分加载，继续执行...")
        except Exception as e:
            logger.error(f"访问签到页面失败: {e}")
            raise Exception(f"无法访问签到页面: {e}")
        
        # 等待签到页面加载（最多重试3次，每次等待15秒）
        if not self.wait_for_checkin_page_loaded(max_retries=3, wait_time=15):
            # 尝试截屏查看当前页面状态
            try:
                self.driver.save_screenshot("checkin_page_debug.png")
                logger.info("已保存签到页面截图供调试")
            except:
                pass
            
            # 检查当前页面内容
            try:
                page_source = self.driver.page_source[:1000]  # 获取前1000个字符
                logger.info(f"当前页面内容片段: {page_source}")
            except:
                pass
            
            raise Exception("签到页面加载失败，无法找到签到相关元素")
        
        # 查找并点击立即签到按钮
        checkin_result = self.find_and_click_checkin_button()
        
        if checkin_result == "already_checked_in":
            return "今日已签到"
        elif checkin_result is True:
            logger.info("已点击立即签到按钮")
            time.sleep(5)  # 等待签到结果
            
            # 获取签到结果
            result_message = self.get_checkin_result()
            return result_message
        else:
            raise Exception("找不到立即签到按钮或按钮不可点击")
    
    def get_checkin_result(self):
        """获取签到结果消息"""
        try:
            # 给页面一些时间显示结果
            time.sleep(3)
            
            # 尝试查找各种可能的成功消息元素
            success_selectors = [
                ".alert-success",
                ".success",
                ".message",
                "[class*='success']",
                "[class*='message']",
                ".modal-content",  # 弹窗内容
                ".ant-message",    # Ant Design 消息
                ".el-message",     # Element UI 消息
                ".toast",          # Toast消息
                ".notification"    # 通知
            ]
            
            for selector in success_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        text = element.text.strip()
                        if text:
                            return text
                except:
                    continue
            
            # 如果没有找到特定元素，检查页面文本
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            important_keywords = ["成功", "签到", "获得", "恭喜", "谢谢", "感谢", "完成", "已签到", "连续签到"]
            
            for keyword in important_keywords:
                if keyword in page_text:
                    # 提取包含关键词的行
                    lines = page_text.split('\n')
                    for line in lines:
                        if keyword in line and len(line.strip()) < 100:  # 避免提取过长的文本
                            return line.strip()
            
            # 检查签到按钮状态变化
            try:
                checkin_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '签到')]")
                for checkin_btn in checkin_btns:
                    if not checkin_btn.is_enabled() or "已签到" in checkin_btn.text:
                        return "今日已签到完成"
            except:
                pass
            
            return "签到完成，但未找到具体结果消息"
            
        except Exception as e:
            return f"获取签到结果时出错: {str(e)}"
    
    def run(self):
        """单个账号执行流程"""
        try:
            logger.info(f"开始处理账号")
            
            # 登录
            if self.login():
                # 签到
                result = self.checkin()
                
                # 获取余额
                balance = self.get_balance()
                
                logger.info(f"签到结果: {result}, 余额: {balance}")
                return True, result, balance
            else:
                raise Exception("登录失败")
                
        except Exception as e:
            error_msg = f"自动签到失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, "未知"
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

class MultiAccountManager:
    """多账号管理器 - 简化配置版本"""
    
    def __init__(self):
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.accounts = self.load_accounts()
    
    def load_accounts(self):
        """从环境变量加载多账号信息，支持冒号分隔多账号和单账号"""
        accounts = []
        
        logger.info("开始加载账号配置...")
        
        # 方法1: 冒号分隔多账号格式
        accounts_str = os.getenv('LEAFLOW_ACCOUNTS', '').strip()
        if accounts_str:
            try:
                logger.info("尝试解析冒号分隔多账号配置")
                account_pairs = [pair.strip() for pair in accounts_str.split(',')]
                
                logger.info(f"找到 {len(account_pairs)} 个账号")
                
                for i, pair in enumerate(account_pairs):
                    if ':' in pair:
                        email, password = pair.split(':', 1)
                        email = email.strip()
                        password = password.strip()
                        
                        if email and password:
                            accounts.append({
                                'email': email,
                                'password': password
                            })
                            logger.info(f"成功添加第 {i+1} 个账号")
                        else:
                            logger.warning(f"账号对格式错误")
                    else:
                        logger.warning(f"账号对缺少冒号分隔符")
                
                if accounts:
                    logger.info(f"从冒号分隔格式成功加载了 {len(accounts)} 个账号")
                    return accounts
                else:
                    logger.warning("冒号分隔配置中没有找到有效的账号信息")
            except Exception as e:
                logger.error(f"解析冒号分隔账号配置失败: {e}")
        
        # 方法2: 单账号格式
        single_email = os.getenv('LEAFLOW_EMAIL', '').strip()
        single_password = os.getenv('LEAFLOW_PASSWORD', '').strip()
        
        if single_email and single_password:
            accounts.append({
                'email': single_email,
                'password': single_password
            })
            logger.info("加载了单个账号配置")
            return accounts
        
        # 如果所有方法都失败
        logger.error("未找到有效的账号配置")
        logger.error("请检查以下环境变量设置:")
        logger.error("1. LEAFLOW_ACCOUNTS: 冒号分隔多账号 (email1:pass1,email2:pass2)")
        logger.error("2. LEAFLOW_EMAIL 和 LEAFLOW_PASSWORD: 单账号")
        
        raise ValueError("未找到有效的账号配置")
    
    def send_notification(self, results):
        """发送汇总通知到Telegram - 按照指定模板格式"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.info("Telegram配置未设置，跳过通知")
            return
        
        try:
            # 构建通知消息 - 避免HTML实体解析错误
            success_count = sum(1 for _, success, _, _ in results if success)
            total_count = len(results)
            current_date = datetime.now().strftime("%Y/%m/%d")
            
            message = "🎁 Leaflow自动签到通知\n"
            message += f"📊 成功: {success_count}/{total_count}\n"
            message += f"📅 签到时间：{current_date}\n\n"
            
            for email, success, result, balance in results:
                # 隐藏邮箱部分字符以保护隐私
                masked_email = email[:3] + "***" + email[email.find("@"):]
                
                if success:
                    status = "✅"
                    message += f"账号：{masked_email}\n"
                    message += f"{status}  {result}！\n"
                    message += f"💰  当前总余额：{balance}。\n\n"
                else:
                    status = "❌"
                    message += f"账号：{masked_email}\n"
                    message += f"{status}  {result}\n\n"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"  # 使用Markdown而不是HTML
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram汇总通知发送成功")
            else:
                logger.error(f"Telegram通知发送失败: {response.text}")
                
        except Exception as e:
            logger.error(f"发送Telegram通知时出错: {e}")
    
    def run_all(self):
        """运行所有账号的签到流程"""
        logger.info(f"开始执行 {len(self.accounts)} 个账号的签到任务")
        
        results = []
        
        for i, account in enumerate(self.accounts, 1):
            logger.info(f"处理第 {i}/{len(self.accounts)} 个账号")
            
            try:
                auto_checkin = LeaflowAutoCheckin(account['email'], account['password'])
                success, result, balance = auto_checkin.run()
                results.append((account['email'], success, result, balance))
                
                # 在账号之间添加间隔，避免请求过于频繁
                if i < len(self.accounts):
                    wait_time = 5
                    logger.info(f"等待{wait_time}秒后处理下一个账号...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                error_msg = f"处理账号时发生异常: {str(e)}"
                logger.error(error_msg)
                results.append((account['email'], False, error_msg, "未知"))
        
        # 发送汇总通知
        self.send_notification(results)
        
        # 返回总体结果
        success_count = sum(1 for _, success, _, _ in results if success)
        return success_count == len(self.accounts), results

def main():
    """主函数"""
    try:
        manager = MultiAccountManager()
        overall_success, detailed_results = manager.run_all()
        
        if overall_success:
            logger.info("✅ 所有账号签到成功")
            exit(0)
        else:
            success_count = sum(1 for _, success, _, _ in detailed_results if success)
            logger.warning(f"⚠️ 部分账号签到失败: {success_count}/{len(detailed_results)} 成功")
            # 即使有失败，也不退出错误状态，因为可能部分成功
            exit(0)
            
    except Exception as e:
        logger.error(f"❌ 脚本执行出错: {e}")
        exit(1)

if __name__ == "__main__":
    main()
