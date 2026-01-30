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
        
        # 通用配置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def close_popup(self):
        """关闭初始弹窗"""
        try:
            logger.info("尝试关闭初始弹窗...")
            time.sleep(3)  # 等待弹窗加载
            
            # 尝试关闭弹窗
            try:
                actions = ActionChains(self.driver)
                actions.move_by_offset(10, 10).click().perform()
                logger.info("已成功关闭弹窗")
                time.sleep(2)
                return True
            except:
                pass
            return False
            
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
            time.sleep(2)
            
            # 尝试多种选择器找到邮箱输入框
            email_selectors = [
                "input[type='text']",
                "input[type='email']", 
                "input[placeholder*='邮箱']",
                "input[placeholder*='邮件']",
                "input[placeholder*='email']",
                "input[name='email']",
                "input[name='username']"
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = self.wait_for_element_clickable(By.CSS_SELECTOR, selector, 5)
                    logger.info(f"找到邮箱输入框")
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
                self.driver.execute_script(f"document.querySelector('input[type=\"text\"], input[type=\"email\"]').value = '{self.email}';")
                logger.info("通过JavaScript设置邮箱")
                time.sleep(2)
            except:
                raise Exception(f"无法输入邮箱: {e}")
        
        # 等待密码输入框出现并输入密码
        try:
            logger.info("查找密码输入框...")
            
            # 等待密码框出现
            password_input = self.wait_for_element_clickable(
                By.CSS_SELECTOR, "input[type='password']", 10
            )
            
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("密码输入完成")
            time.sleep(1)
            
        except Exception as e:
            raise Exception("找不到密码输入框")
        
        # 点击登录按钮
        try:
            logger.info("查找登录按钮...")
            login_btn_selectors = [
                "//button[contains(text(), '登录')]",
                "//button[contains(text(), 'Login')]",
                "//button[@type='submit']",
                "//input[@type='submit']",
                "button[type='submit']"
            ]
            
            login_btn = None
            for selector in login_btn_selectors:
                try:
                    if selector.startswith("//"):
                        login_btn = self.wait_for_element_clickable(By.XPATH, selector, 5)
                    else:
                        login_btn = self.wait_for_element_clickable(By.CSS_SELECTOR, selector, 5)
                    logger.info(f"找到登录按钮")
                    break
                except:
                    continue
            
            if not login_btn:
                raise Exception("找不到登录按钮")
            
            login_btn.click()
            logger.info("已点击登录按钮")
            
        except Exception as e:
            raise Exception(f"点击登录按钮失败: {e}")
        
        # 等待登录完成
        try:
            WebDriverWait(self.driver, 20).until(
                lambda driver: "dashboard" in driver.current_url or "workspaces" in driver.current_url or "login" not in driver.current_url
            )
            
            # 检查当前URL确认登录成功
            current_url = self.driver.current_url
            if "dashboard" in current_url or "workspaces" in current_url or "login" not in current_url:
                logger.info(f"登录成功，当前URL: {current_url}")
                return True
            else:
                raise Exception("登录后未跳转到正确页面")
                
        except Exception as e:
            # 检查是否登录失败
            try:
                error_selectors = [".error", ".alert-danger", "[class*='error']", "[class*='danger']"]
                for selector in error_selectors:
                    try:
                        error_msg = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if error_msg.is_displayed():
                            raise Exception(f"登录失败: {error_msg.text}")
                    except:
                        continue
                raise Exception(f"登录超时，无法确认登录状态: {e}")
            except Exception as e2:
                raise e2
    
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
                "//span[contains(@class, 'font-medium')]"
            ]
            
            for selector in balance_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # 查找包含数字和货币符号的文本
                        if any(char.isdigit() for char in text) and ('¥' in text or '￥' in text or '元' in text):
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
    
    def checkin(self):
        """执行签到流程"""
        logger.info("跳转到签到页面...")
        
        # 跳转到签到页面
        self.driver.get("https://checkin.leaflow.net")
        
        # 等待签到页面加载
        try:
            logger.info("等待签到页面加载...")
            # 等待页面主要元素加载
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            # 检查页面标题
            page_title = self.driver.title
            logger.info(f"页面标题: {page_title}")
            
            # 检查是否包含"每日签到"
            page_source = self.driver.page_source
            if "每日签到" in page_source:
                logger.info("签到页面加载成功")
            else:
                logger.warning("签到页面可能未正确加载")
                
        except Exception as e:
            logger.error(f"签到页面加载失败: {e}")
            raise Exception(f"签到页面加载失败: {e}")
        
        # 查找并处理签到按钮
        return self.find_and_click_checkin_button()
    
    def find_and_click_checkin_button(self):
        """查找并处理签到按钮"""
        try:
            logger.info("查找签到按钮...")
            time.sleep(3)
            
            # 根据HTML源码，签到按钮有多个可能的标识
            checkin_selectors = [
                "button.checkin-btn",  # CSS类选择器
                "//button[contains(@class, 'checkin-btn')]",  # XPath
                "//button[contains(text(), '立即签到')]",  # 立即签到按钮
                "//button[contains(text(), '已完成')]",  # 已完成按钮
                "//button[contains(text(), '今日已签到')]",  # 今日已签到按钮
            ]
            
            checkin_btn = None
            for selector in checkin_selectors:
                try:
                    if selector.startswith("//"):
                        checkin_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        checkin_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if checkin_btn:
                        logger.info(f"找到签到按钮: {checkin_btn.text}")
                        break
                except:
                    continue
            
            if not checkin_btn:
                # 尝试通过页面文本判断状态
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "今日已签到" in page_text:
                    return "今日已签到"
                elif "立即签到" in page_text:
                    # 重新查找立即签到按钮
                    try:
                        checkin_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '立即签到')]")
                    except:
                        raise Exception("找不到签到按钮")
                else:
                    raise Exception("无法确定签到状态")
            
            # 检查按钮状态
            btn_text = checkin_btn.text.strip()
            btn_enabled = checkin_btn.is_enabled()
            
            logger.info(f"按钮文本: {btn_text}, 是否可用: {btn_enabled}")
            
            if "已签到" in btn_text or "已完成" in btn_text or not btn_enabled:
                # 获取奖励金额
                reward = self.get_checkin_reward()
                return f"今日已签到{reward}"
            else:
                # 点击签到按钮
                logger.info("点击立即签到按钮")
                checkin_btn.click()
                time.sleep(5)
                
                # 获取签到结果
                result = self.get_checkin_result()
                return result
                
        except Exception as e:
            logger.error(f"处理签到按钮时出错: {e}")
            
            # 尝试通过页面内容判断
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "今日已签到" in page_text:
                    reward = self.get_checkin_reward()
                    return f"今日已签到{reward}"
                elif "立即签到" in page_text:
                    raise Exception("找到立即签到按钮但无法点击")
                else:
                    raise Exception(f"无法处理签到: {e}")
            except:
                raise Exception(f"签到失败: {e}")
    
    def get_checkin_reward(self):
        """获取签到奖励金额"""
        try:
            # 查找奖励金额元素
            reward_selectors = [
                "//div[contains(@class, 'reward-amount')]",
                "//div[contains(text(), '+') and contains(text(), '元')]",
                "//div[contains(@class, 'text-success') and contains(text(), '+')]"
            ]
            
            for selector in reward_selectors:
                try:
                    reward_element = self.driver.find_element(By.XPATH, selector)
                    reward_text = reward_element.text.strip()
                    if reward_text:
                        return f"，获得{reward_text}"
                except:
                    continue
            
            return ""
        except:
            return ""
    
    def get_checkin_result(self):
        """获取签到结果消息"""
        try:
            # 等待结果显示
            time.sleep(3)
            
            # 查找可能的成功消息
            success_selectors = [
                "//div[contains(@class, 'checkin-status')]",
                "//div[contains(@class, 'text-success')]",
                "//div[contains(text(), '签到成功')]",
                "//div[contains(text(), '获得')]",
                "//div[contains(text(), '恭喜')]",
                "//div[contains(@class, 'reward-amount')]"
            ]
            
            result_parts = []
            for selector in success_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            text = element.text.strip()
                            if text and len(text) < 100:  # 避免过长的文本
                                result_parts.append(text)
                except:
                    continue
            
            # 去除重复
            unique_results = []
            for result in result_parts:
                if result not in unique_results:
                    unique_results.append(result)
            
            if unique_results:
                return "签到成功：" + "，".join(unique_results[:3])  # 最多显示3条结果
            
            # 如果找不到特定结果，检查签到按钮状态
            try:
                checkin_btn = self.driver.find_element(By.CSS_SELECTOR, "button.checkin-btn")
                if not checkin_btn.is_enabled() or "已签到" in checkin_btn.text:
                    return "今日已签到完成"
            except:
                pass
            
            return "签到完成"
            
        except Exception as e:
            return f"签到完成，但未获取到详细结果: {str(e)}"
    
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
                self.driver.quit()

# 以下MultiAccountManager类和main函数保持不变，与原始代码相同
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
            # 构建通知消息
            success_count = sum(1 for _, success, _, _ in results if success)
            total_count = len(results)
            current_date = datetime.now().strftime("%Y/%m/%d")
            
            message = f"🎁 Leaflow自动签到通知\n"
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
                "parse_mode": "HTML"
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
