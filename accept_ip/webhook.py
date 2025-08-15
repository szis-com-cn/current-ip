from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import logging
import re
import os
import subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pydantic import BaseModel
from typing import Optional, Dict, Any
from crypto_utils import CryptoManager
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 创建 FastAPI 应用
app = FastAPI(title="IP Access Control API", version="1.0.0")

# 配置管理类
class Config:
    """配置管理类，从 .env 文件读取配置"""
    def __init__(self):
        # 统一密钥配置：用于加密与 API 请求头校验
        self.CRYPTO_SECRET_KEY = os.getenv('CRYPTO_SECRET_KEY', '')
        
        # 日志配置
        self.LOG_FILE = os.getenv('LOG_FILE', '/app/logs/webhook.log')
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # Nginx 配置
        self.NGINX_CONFIG_PATH = os.getenv('NGINX_CONFIG_PATH', '/etc/nginx/conf.d/allowed_ips.conf')
        
        # API 配置（统一密钥策略）
        self.API_KEY_HEADER = os.getenv('API_KEY_HEADER', 'X-API-Key')
        # 存在有效密钥则启用校验与加密，否则明文模式
        self.REQUIRE_API_KEY = bool(self.CRYPTO_SECRET_KEY) and self.CRYPTO_SECRET_KEY != 'your_secret_key_here'
        # API_KEY 等于 CRYPTO_SECRET_KEY（避免单独配置）
        self.API_KEY = self.CRYPTO_SECRET_KEY if self.REQUIRE_API_KEY else ''

# 初始化配置
config = Config()

# 配置日志
def setup_logging():
    """配置日志系统，记录到文件和控制台"""
    # 创建日志目录
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 设置日志级别
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    
    # 创建 logger
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    
    # 清除现有的 handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建文件 handler（轮转日志）
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # 创建控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加 handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 初始化日志
logger = setup_logging()

# API Key 验证中间件
async def verify_api_key(request: Request):
    """验证 API Key"""
    if not config.REQUIRE_API_KEY:
        return True
    
    # 从请求头获取 API Key
    api_key = request.headers.get(config.API_KEY_HEADER)
    
    # 如果没有提供 API Key
    if not api_key:
        logger.warning(f"请求缺少 API Key: {request.url}")
        raise HTTPException(status_code=401, detail="Missing API Key")
    
    # 验证 API Key（使用配置的 API Key）
    if api_key != config.API_KEY:
        logger.warning(f"无效的 API Key: {api_key[:8]}*** from {request.client.host}")
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    logger.info(f"API Key 验证成功 from {request.client.host}")
    return True

# 数据模型
class WebhookData(BaseModel):
    """Webhook 数据模型"""
    current_ip: Optional[str] = None
    previous_ip: Optional[str] = None
    timestamp: Optional[str] = None
    encryption_enabled: Optional[bool] = None
    encrypted_data: Optional[str] = None
    signature: Optional[str] = None
    type: Optional[str] = None
    message: Optional[str] = None
    text: Optional[str] = None
    content: Optional[str] = None
    notification_result: Optional[str] = None

class NginxIPManager:
    """Nginx IP地址管理器，用于处理IP地址更新和Nginx配置"""
    
    def __init__(self, config_path=None):
        """
        初始化Nginx IP管理器
        
        Args:
            config_path (str): Nginx配置文件路径
        """
        self.nginx_config_path = config_path or config.NGINX_CONFIG_PATH
        self.logger = logging.getLogger(__name__)
        
        # 初始化加密管理器（如果提供了密钥）
        self.crypto_manager = None
        if config.CRYPTO_SECRET_KEY:
            self.crypto_manager = CryptoManager(config.CRYPTO_SECRET_KEY)
            self.logger.info("加密功能已启用")
        else:
            self.logger.warning("未设置加密密钥，将使用明文模式")
    
    def decrypt_webhook_data(self, data):
        """
        解密Webhook数据
        
        Args:
            data (dict): 接收到的数据
            
        Returns:
            dict: 解密后的数据或原始数据
        """
        # 检查是否为加密数据
        if isinstance(data, dict) and data.get('encryption_enabled') and 'encrypted_data' in data:
            if not self.crypto_manager:
                raise ValueError("接收到加密数据但未配置解密密钥")
            
            # 验证签名
            encrypted_data = data['encrypted_data']
            signature = data.get('signature', '')
            
            if not self.crypto_manager.verify_signature(encrypted_data, signature):
                raise ValueError("数据签名验证失败")
            
            # 解密数据
            decrypted_data = self.crypto_manager.decrypt_data(encrypted_data)
            self.logger.info("成功解密Webhook数据")
            return decrypted_data
        else:
            # 明文数据或测试数据
            if data.get('type') == 'connection_test':
                self.logger.info("接收到连接测试请求")
            return data
    
    def extract_ip_from_data(self, data):
        """
        从Webhook数据中提取IP地址
        
        Args:
            data (dict or str): Webhook接收到的数据
            
        Returns:
            str or None: 提取到的IP地址，如果未找到则返回None
        """
        # 如果数据是字典格式
        if isinstance(data, dict):
            # 跳过测试请求
            if data.get('type') == 'connection_test':
                return None
                
            # 优先从current_ip字段中提取新IP地址
            if 'current_ip' in data and data['current_ip']:
                # 从current_ip字段中提取IP
                ip_value = data['current_ip']
                # 如果IP值是字符串类型，需要去除引号和换行符
                if isinstance(ip_value, str):
                    # 去除首尾的空白字符（包括换行符）
                    ip_value = ip_value.strip()
                    # 去除首尾的双引号
                    ip_value = ip_value.strip('"')
                    # 去除首尾的单引号
                    ip_value = ip_value.strip("'")
                
                # 验证IP地址格式
                ip_pattern = r'^([0-9]{1,3}\.){3}[0-9]{1,3}$'
                if re.match(ip_pattern, ip_value):
                    return ip_value
            
            # 如果current_ip为空或无效，则尝试从previous_ip字段中提取IP
            elif 'previous_ip' in data and data['previous_ip']:
                # 从previous_ip字段中提取IP
                ip_value = data['previous_ip']
                # 如果IP值是字符串类型，需要去除引号和换行符
                if isinstance(ip_value, str):
                    # 去除首尾的空白字符（包括换行符）
                    ip_value = ip_value.strip()
                    # 去除首尾的双引号
                    ip_value = ip_value.strip('"')
                    # 去除首尾的单引号
                    ip_value = ip_value.strip("'")
                
                # 验证IP地址格式
                ip_pattern = r'^([0-9]{1,3}\.){3}[0-9]{1,3}$'
                if re.match(ip_pattern, ip_value):
                    return ip_value
            
            # 其他字段的处理保持不变
            elif 'text' in data:
                # 直接从text字段中提取IP
                ip_pattern = r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)'
                match = re.search(ip_pattern, data['text'])
                if match:
                    return match.group(1)
            elif 'content' in data:
                ip_pattern = r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)'
                match = re.search(ip_pattern, data['content'])
                if match:
                    return match.group(1)
        else:
            # 如果数据是字符串格式
            ip_pattern = r'当前公网IP地址为:"([0-9.]+)"'
            match = re.search(ip_pattern, str(data))
            if match:
                return match.group(1)
            
            # 尝试其他可能的IP格式
            ip_pattern = r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)'
            match = re.search(ip_pattern, str(data))
            if match:
                return match.group(1)
        
        return None
    
    def read_current_ips(self):
        """
        读取当前Nginx配置文件中的IP地址列表
        
        Returns:
            set: 当前允许的IP地址集合
        """
        allowed_ips = set()
        
        if os.path.exists(self.nginx_config_path):
            try:
                with open(self.nginx_config_path, 'r') as f:
                    content = f.read()
                    # 提取现有IP地址
                    ip_pattern = r'allow ([0-9.]+);'
                    existing_ips = re.findall(ip_pattern, content)
                    allowed_ips.update(existing_ips)
            except Exception as e:
                self.logger.error(f"读取Nginx配置文件时发生错误: {str(e)}")
        
        return allowed_ips
    
    def update_nginx_config(self, new_ip):
        """
        更新Nginx配置文件，添加新的IP地址
        
        Args:
            new_ip (str): 要添加的新IP地址
            
        Returns:
            bool: 是否成功更新配置
        """
        # 读取现有配置
        allowed_ips = self.read_current_ips()
        
        # 检查IP是否已经存在
        if new_ip in allowed_ips:
            self.logger.info(f"IP地址 {new_ip} 已经存在于配置文件中，无需更新")
            return False
        
        # 添加新IP
        allowed_ips.add(new_ip)
        
        # 生成新的配置内容
        config_content = "# 允许访问的IP地址列表\n"
        for ip in allowed_ips:
            config_content += f"allow {ip};\n"
        config_content += "deny all;\n"
        
        # 写入配置文件
        try:
            with open(self.nginx_config_path, 'w') as f:
                f.write(config_content)
            self.logger.info(f"已更新Nginx配置文件，添加IP: {new_ip}")
            return True
        except Exception as e:
            self.logger.error(f"写入Nginx配置文件时发生错误: {str(e)}")
            return False
    
    def reload_nginx(self):
        """
        平滑重启Nginx服务
        该方法首先尝试在容器内直接平滑重启Nginx，
        如果失败则使用docker restart重启整个容器
        """
        nginx_container_name = 'ip-nginx-1'
        
        try:
            # 首先尝试在nginx容器内直接平滑重启Nginx
            self.logger.info("尝试在容器内平滑重启Nginx")
            
            # 检查Nginx配置文件是否正确
            check_result = subprocess.run(['docker', 'exec', nginx_container_name, 'nginx', '-t'], 
                                        capture_output=True, text=True, timeout=10)
            
            if check_result.returncode != 0:
                self.logger.error(f"Nginx配置文件检查失败: {check_result.stderr}")
                return False
            
            # 在容器内平滑重启Nginx
            reload_result = subprocess.run(['docker', 'exec', nginx_container_name, 'nginx', '-s', 'reload'], 
                                         capture_output=True, text=True, timeout=10)
            
            if reload_result.returncode == 0:
                self.logger.info("Nginx服务已平滑重启")
                return True
            else:
                self.logger.warning(f"容器内平滑重启失败: {reload_result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.warning("容器内Nginx重启超时")
        except Exception as e:
            self.logger.warning(f"容器内重启Nginx时发生错误: {str(e)}")
            
            # 如果容器内重启失败，则使用docker restart重启整个容器
            try:
                self.logger.info("尝试重启整个Nginx容器")
                restart_result = subprocess.run(['docker', 'restart', nginx_container_name], 
                                              capture_output=True, text=True, timeout=30)
                
                if restart_result.returncode == 0:
                    self.logger.info("Nginx容器已重启")
                    return True
                else:
                    self.logger.error(f"Nginx容器重启失败: {restart_result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                self.logger.error("Nginx容器重启超时")
                return False
            except Exception as e:
                self.logger.error(f"重启Nginx容器时发生错误: {str(e)}")
                return False

    def get_nginx_http_status(self):
        """
        获取Nginx服务的HTTP状态
        
        Returns:
            tuple: (status_code, error_message)
        """
        nginx_container_name = 'ip-nginx-1'
        
        try:
            # 检查Nginx容器是否运行
            check_result = subprocess.run(
                ['docker', 'inspect', '--format={{.State.Status}}', nginx_container_name],
                capture_output=True, text=True, timeout=5
            )
            
            if check_result.returncode != 0:
                return None, f"无法检查Nginx容器状态: {check_result.stderr}"
            
            container_status = check_result.stdout.strip()
            if container_status != 'running':
                return None, f"Nginx容器未运行，当前状态: {container_status}"
            
            # 尝试获取Nginx状态
            try:
                import requests
                response = requests.get('http://ip-nginx-1/', timeout=3)
                return response.status_code, None
            except ImportError:
                # 如果没有requests库，使用curl
                curl_result = subprocess.run(
                    ['docker', 'exec', nginx_container_name, 'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost/'],
                    capture_output=True, text=True, timeout=5
                )
                
                if curl_result.returncode == 0:
                    return int(curl_result.stdout.strip()), None
                else:
                    return None, f"无法获取Nginx HTTP状态: {curl_result.stderr}"
            except Exception as e:
                return None, f"Nginx HTTP检查失败: {str(e)}"
                
        except subprocess.TimeoutExpired:
            return None, "检查Nginx状态超时"
        except Exception as e:
            return None, f"检查Nginx状态时发生错误: {str(e)}"


@app.get('/health')
async def health_check():
    """健康检查端点"""
    return JSONResponse({"status": "healthy", "service": "webhook"}, status_code=200)

@app.post('/webhook')
async def webhook(request: Request):
    """Webhook 接收端点，支持加密/明文数据，带 API Key 校验"""
    try:
        # API Key 验证
        await verify_api_key(request)
        
        logger.info(f"接收到请求: {request.method} {request.url}")
        # 仅记录请求头键名，并对 API Key 做脱敏
        header_names = list(request.headers.keys())
        if config.API_KEY_HEADER in request.headers:
            redacted = request.headers.get(config.API_KEY_HEADER)
            if redacted:
                redacted = redacted[:3] + '***' + redacted[-3:]
            logger.info(f"请求头包含 {config.API_KEY_HEADER}: {bool(redacted)} ({redacted})；所有键: {header_names}")
        else:
            logger.info(f"请求头键名: {header_names}")
        
        # 验证请求内容类型
        content_type = request.headers.get('content-type', '')
        if 'application/json' not in content_type:
            logger.warning("请求内容类型不是JSON")
            raise HTTPException(status_code=415, detail="invalid content type, expected application/json")

        # 获取并验证JSON数据
        data = await request.json()
        if not data:
            logger.warning("接收到空的JSON数据")
            raise HTTPException(status_code=400, detail="empty json data")

        # 处理Webhook数据
        logger.info(f"接收到的Webhook数据: {data}")
        result = process_webhook_data(data)  # 获取处理结果摘要

        # 附带 Nginx 的HTTP状态码
        manager = NginxIPManager()
        nginx_http_status, nginx_status_error = manager.get_nginx_http_status()

        response_body = {
            'status': 'success',
            'nginx_http_status': nginx_http_status,
            'nginx_status_error': nginx_status_error,
            'timestamp': datetime.utcnow().isoformat()
        }
        if isinstance(result, dict):
            response_body.update(result)

        return JSONResponse(response_body, status_code=200)

    except HTTPException as e:
        # 直接抛出的 HTTP 异常
        return JSONResponse({"status": "error", "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        return JSONResponse({'status': 'error', 'message': str(e)}, status_code=500)


def process_webhook_data(data):
    """处理Webhook数据的函数，提取IP地址并更新Nginx配置"""
    # 创建Nginx IP管理器实例
    nginx_manager = NginxIPManager()
    
    try:
        # 解密数据（如果是加密的）
        decrypted_data = nginx_manager.decrypt_webhook_data(data)
        
        # 提取IP地址
        current_ip = nginx_manager.extract_ip_from_data(decrypted_data)
        
        if current_ip:
            logger.info(f"提取到IP地址: {current_ip}")
            
            # 更新Nginx配置文件
            if nginx_manager.update_nginx_config(current_ip):
                # 重启Nginx服务
                if nginx_manager.reload_nginx():
                    logger.info("Nginx配置已更新并成功重启")
                else:
                    logger.error("Nginx配置已更新但重启失败")
        else:
            logger.warning("未能从数据中提取到IP地址")
            
    except ValueError as e:
        logger.error(f"数据处理失败: {str(e)}")
    except Exception as e:
        logger.error(f"处理Webhook数据时发生未知错误: {str(e)}")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000, log_level='info')