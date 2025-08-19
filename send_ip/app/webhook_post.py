import requests
import logging
from logging.handlers import RotatingFileHandler
import time
from .crypto_utils import CryptoManager
import configparser

# 全局日志配置（避免重复添加handler）
def get_logger():
    
     # 配置读取、日志设置等逻辑保持不变...
    file = '.env'
    con = configparser.ConfigParser()
    con.read(file, encoding='utf-8')

    file_name = dict(con.items('file_name'))
    
    logger = logging.getLogger(__name__)
    if not logger.handlers:  # 仅在没有handler时添加，避免重复日志
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            file_name["log_file"],
            maxBytes=1024*1024*5,  # 5MB
            backupCount=3,
            encoding="utf-8"
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def test_webhook_connection(webhook, secret_key=None):
    """
    测试 Webhook 有效性。
    - 当提供 secret_key 时：
      1) 使用对称加密对测试载荷进行加密，并携带签名；
      2) 在请求头中附带统一密钥头 X-API-Key=secret_key 以通过服务端校验。
    - 当未提供 secret_key 时：明文发送，不附带头。
    返回 (ok: bool, msg: str)
    """
    logger = get_logger()
    try:
        # 发送测试专用内容，包含明确的测试标识
        test_payload = {
            "type": "connection_test",  # 接收方可通过此字段识别为测试
            "message": "Webhook connection test (no action required)",
            "timestamp": str(time.time())
        }
        
        headers = {}
        
        # 如果提供了密钥，则加密测试数据并附加统一密钥请求头
        if secret_key:
            crypto_manager = CryptoManager(secret_key)
            encrypted_data = crypto_manager.encrypt_data(test_payload)
            signature = crypto_manager.generate_signature(encrypted_data)
            
            final_payload = {
                "encrypted_data": encrypted_data,
                "signature": signature,
                "encryption_enabled": True
            }
            headers["X-API-Key"] = secret_key
        else:
            final_payload = test_payload
        
        response = requests.post(
            webhook,
            json=final_payload,
            headers=headers if headers else None,
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


def webhook_p(old_ip, new_ip, webhook, now_time, if_post, secret_key=None):
    """
    发送实际业务 Webhook。
    - 当提供 secret_key 时，进行对称加密并附带 X-API-Key=secret_key 请求头；
    - 当未提供 secret_key 时，按明文发送。
    """
    logger = get_logger()
    
    content = {
        "current_ip": new_ip,
        "previous_ip": old_ip,
        "timestamp": now_time,
        "notification_result": if_post
    }
    
    try:
        headers = {}
        # 如果提供了密钥，则加密数据并附带统一密钥请求头
        if secret_key:
            crypto_manager = CryptoManager(secret_key)
            encrypted_data = crypto_manager.encrypt_data(content)
            signature = crypto_manager.generate_signature(encrypted_data)
            
            final_payload = {
                "encrypted_data": encrypted_data,
                "signature": signature,
                "encryption_enabled": True
            }
            headers["X-API-Key"] = secret_key
            logger.info("使用加密模式发送Webhook数据（含X-API-Key）")
        else:
            final_payload = content
            logger.info("使用明文模式发送Webhook数据")
        
        response = requests.post(
            webhook,
            json=final_payload,
            headers=headers if headers else None,
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
