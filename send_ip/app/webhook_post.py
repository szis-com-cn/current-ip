import requests
import logging
from logging.handlers import RotatingFileHandler
import time

# 全局日志配置（避免重复添加handler）
def get_logger():
    logger = logging.getLogger(__name__)
    if not logger.handlers:  # 仅在没有handler时添加，避免重复日志
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            "log.txt",
            maxBytes=1024*1024*5,  # 5MB
            backupCount=3,
            encoding="utf-8"
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def test_webhook_connection(webhook):
    """测试Webhook有效性，发送特殊标识的测试请求，不干扰业务"""
    logger = get_logger()
    try:
        # 发送测试专用内容，包含明确的测试标识
        test_payload = {
            "type": "connection_test",  # 接收方可通过此字段识别为测试
            "message": "Webhook connection test (no action required)",
            "timestamp": str(time.time())
        }
        
        response = requests.post(
            webhook,
            json=test_payload,
            timeout=8
        )
        
        # 记录测试结果
        logger.info(f"Webhook测试响应 - 状态码: {response.status_code}")
        
        # 验证逻辑：状态码200-299视为有效
        if 200 <= response.status_code < 300:
            return True, f"测试成功 (状态码: {response.status_code})"
        else:
            return False, f"测试失败 (状态码: {response.status_code})"
            
    except requests.exceptions.ConnectionError:
        return False, "连接失败（无法访问Webhook地址）"
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except Exception as e:
        return False, f"测试异常: {str(e)}"


def webhook_p(old_ip, new_ip, webhook, now_time, if_post):
    logger = get_logger()
    
    content = {
        "current_ip": new_ip,
        "previous_ip": old_ip,
        "timestamp": now_time,
        "notification_result": if_post
    }
    
    try:
        response = requests.post(
            webhook,
            json=content,
            timeout=5
        )
        logger.info(f"Webhook发送响应 - 状态码: {response.status_code}")
        try:
            logger.info(f"Webhook响应内容: {response.json()}")
        except:
            logger.info(f"Webhook响应内容: {response.text[:200]}")  # 非JSON响应
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Webhook连接错误: {e}")
    except Exception as e:
        logger.error(f"Webhook发送错误: {e}")
