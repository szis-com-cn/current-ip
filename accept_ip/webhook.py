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
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 创建 FastAPI 应用
app = FastAPI(title="IP Access Control API", version="1.0.0")

# 配置管理类
class Config:
    """配置管理类，从 .env 文件读取配置"""
    def __init__(self):
        # 日志配置
        self.LOG_FILE = os.getenv('LOG_FILE', '/app/logs/webhook.log')
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # Nginx 配置
        self.NGINX_CONFIG_PATH = os.getenv('NGINX_CONFIG_PATH', '/etc/nginx/conf.d/allowed_ips.conf')
        self.NGINX_RELOAD_METHOD = os.getenv('NGINX_RELOAD_METHOD', 'external')  # container|external|command
        self.NGINX_CONTAINER_NAME = os.getenv('NGINX_CONTAINER_NAME', 'nginx')
        self.NGINX_RELOAD_COMMAND = os.getenv('NGINX_RELOAD_COMMAND', 'nginx -s reload')

# 初始化配置
config = Config()

# 日志设置
def get_logger(name: str) -> logging.Logger:
    """获取配置好的 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 创建日志目录
        os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
        
        # 文件处理器
        file_handler = RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=config.LOG_MAX_SIZE,
            backupCount=config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

logger = get_logger(__name__)

class IPWhitelistManager:
    """IP 白名单数据模型"""
    def __init__(self):
        self.allowed_ips = set()
    
    def add_ip(self, ip: str) -> bool:
        """
        添加 IP 到白名单
        Args:
            ip: 要添加的 IP 地址
        Returns:
            bool: 是否成功添加
        """
        if self._is_valid_ip(ip):
            self.allowed_ips.add(ip)
            return True
        return False
    
    def remove_ip(self, ip: str) -> bool:
        """
        从白名单移除 IP
        Args:
            ip: 要移除的 IP 地址
        Returns:
            bool: 是否成功移除
        """
        if ip in self.allowed_ips:
            self.allowed_ips.remove(ip)
            return True
        return False
    
    def get_ips(self) -> list:
        """获取所有白名单 IP"""
        return sorted(list(self.allowed_ips))
    
    def _is_valid_ip(self, ip: str) -> bool:
        """验证 IP 格式"""
        pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        return bool(re.match(pattern, ip))

# 数据模型
class WebhookData(BaseModel):
    """Webhook 数据模型"""
    current_ip: Optional[str] = None
    previous_ip: Optional[str] = None
    timestamp: Optional[str] = None
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
        self.whitelist_manager = IPWhitelistManager()
        self._load_existing_ips()
    
    def _load_existing_ips(self):
        """加载现有的 IP 配置"""
        try:
            if os.path.exists(self.nginx_config_path):
                with open(self.nginx_config_path, 'r') as f:
                    content = f.read()
                    # 解析现有的 IP 配置
                    ip_pattern = r'allow\s+(\d+\.\d+\.\d+\.\d+);'
                    ips = re.findall(ip_pattern, content)
                    for ip in ips:
                        self.whitelist_manager.add_ip(ip)
                self.logger.info(f"成功加载 {len(ips)} 个现有 IP 配置")
        except Exception as e:
            self.logger.error(f"加载现有 IP 配置失败: {e}")
    
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
            
            # 尝试从ip字段中提取IP地址
            elif 'ip' in data and data['ip']:
                # 从ip字段中提取IP
                ip_value = data['ip']
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
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.nginx_config_path), exist_ok=True)
            
            with open(self.nginx_config_path, 'w') as f:
                f.write(config_content)
            self.logger.info(f"已更新Nginx配置文件，添加IP: {new_ip}")
            return True
        except Exception as e:
            self.logger.error(f"写入Nginx配置文件时发生错误: {str(e)}")
            return False
    
    def reload_nginx(self):
        """
        根据配置的方法重载Nginx服务
        """
        try:
            if config.NGINX_RELOAD_METHOD == 'container':
                return self._reload_nginx_container()
            elif config.NGINX_RELOAD_METHOD == 'command':
                return self._reload_nginx_command()
            elif config.NGINX_RELOAD_METHOD == 'external':
                self.logger.info("使用外部Nginx容器模式重载")
                return self._reload_nginx_container()
            else:
                self.logger.error(f"不支持的Nginx重载方法: {config.NGINX_RELOAD_METHOD}")
                return False
        except Exception as e:
            self.logger.error(f"重载Nginx时发生错误: {str(e)}")
            return False
    
    def _reload_nginx_container(self):
        """通过Docker容器重载Nginx"""
        nginx_container_name = config.NGINX_CONTAINER_NAME
        
        try:
            # 检查Nginx配置文件是否正确
            check_result = subprocess.run([
                'docker', 'exec', nginx_container_name, 'nginx', '-t'
            ], capture_output=True, text=True, timeout=10)
            
            if check_result.returncode != 0:
                self.logger.error(f"Nginx配置文件检查失败: {check_result.stderr}")
                return False
            
            # 在容器内平滑重启Nginx
            reload_result = subprocess.run([
                'docker', 'exec', nginx_container_name, 'nginx', '-s', 'reload'
            ], capture_output=True, text=True, timeout=10)
            
            if reload_result.returncode == 0:
                self.logger.info("Nginx服务已平滑重启")
                return True
            else:
                self.logger.error(f"容器内平滑重启失败: {reload_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("容器内Nginx重启超时")
            return False
        except Exception as e:
            self.logger.error(f"容器内重启Nginx时发生错误: {str(e)}")
            return False
    
    def _reload_nginx_command(self):
        """通过自定义命令重载Nginx"""
        try:
            reload_result = subprocess.run(
                config.NGINX_RELOAD_COMMAND.split(),
                capture_output=True, text=True, timeout=10
            )
            
            if reload_result.returncode == 0:
                self.logger.info(f"Nginx重载成功: {config.NGINX_RELOAD_COMMAND}")
                return True
            else:
                self.logger.error(f"Nginx重载失败: {reload_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Nginx重载命令超时")
            return False
        except Exception as e:
            self.logger.error(f"执行Nginx重载命令时发生错误: {str(e)}")
            return False

    def get_nginx_status(self):
        """获取Nginx服务状态信息 - 仅显示重载方式信息"""
        if config.NGINX_RELOAD_METHOD == 'external':
            return {'status': 'external', 'message': f'使用外部Nginx服务 ({config.NGINX_CONTAINER_NAME})'}
        
        if config.NGINX_RELOAD_METHOD == 'container':
            return {'status': 'container', 'message': f'使用容器重载方式 ({config.NGINX_CONTAINER_NAME})'}
        
        # 对于command方法
        return {'status': 'command', 'message': f'使用自定义命令重载方式 ({config.NGINX_RELOAD_COMMAND})'}


@app.get('/health')
async def health_check():
    """健康检查端点"""
    # 获取Nginx状态信息
    manager = NginxIPManager()
    nginx_status = manager.get_nginx_status()
    
    # 记录Nginx状态信息到日志
    logger.info(f"健康检查 - 外部Nginx状态: {nginx_status['status']} - {nginx_status['message']}")
    
    return JSONResponse({
        "status": "healthy", 
        "service": "webhook",
        "nginx_status": nginx_status,
        "timestamp": datetime.utcnow().isoformat()
    }, status_code=200)

@app.post('/webhook')
async def webhook(request: Request):
    """Webhook 接收端点，处理明文数据"""
    try:
        logger.info(f"接收到请求: {request.method} {request.url}")
        
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
        result = process_webhook_data(data)

        # 获取Nginx状态信息
        manager = NginxIPManager()
        nginx_status = manager.get_nginx_status()
        
        # 记录Nginx状态信息到日志
        logger.info(f"外部Nginx状态: {nginx_status['status']} - {nginx_status['message']}")

        response_body = {
            'status': 'success',
            'nginx_status': nginx_status,
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
        # 跳过测试请求，不记录警告
        if isinstance(data, dict) and data.get('type') == 'connection_test':
            return {'message': '连接测试请求，已跳过处理'}
        
        # 提取IP地址（明文处理）
        current_ip = nginx_manager.extract_ip_from_data(data)
        
        if current_ip:
            logger.info(f"提取到IP地址: {current_ip}")
            
            # 更新Nginx配置文件
            if nginx_manager.update_nginx_config(current_ip):
                # 获取并记录当前Nginx状态
                nginx_status = nginx_manager.get_nginx_status()
                logger.info(f"配置更新后 - 外部Nginx状态: {nginx_status['status']} - {nginx_status['message']}")
                
                # 重启Nginx服务
                if nginx_manager.reload_nginx():
                    # 重载后再次检查状态
                    nginx_status_after = nginx_manager.get_nginx_status()
                    logger.info(f"Nginx重载后状态: {nginx_status_after['status']} - {nginx_status_after['message']}")
                    return {'ip_added': current_ip, 'nginx_reloaded': True}
                else:
                    logger.error("Nginx配置已更新但重启失败")
                    # 记录重载失败后的状态
                    nginx_status_failed = nginx_manager.get_nginx_status()
                    logger.error(f"重载失败后 - 外部Nginx状态: {nginx_status_failed['status']} - {nginx_status_failed['message']}")
                    return {'ip_added': current_ip, 'nginx_reloaded': False}
            else:
                return {'message': f'IP {current_ip} 已存在，无需更新'}
        else:
            logger.warning("未能从数据中提取到IP地址")
            return {'message': '未能从数据中提取到IP地址'}
            
    except Exception as e:
        logger.error(f"处理Webhook数据时发生错误: {str(e)}")
        return {'error': str(e)}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000, log_level='info')