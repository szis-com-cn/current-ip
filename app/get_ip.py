import requests
import configparser
import json
import time
import ast
from typing import Tuple, Optional, Dict, Any

# 免费的公共 IP 查询服务列表
'''
PUBLIC_IP_APIS = [
    {"url": "https://api.ipify.org?format=json", "name": "ipify", "parser": lambda x: x["ip"]},
    {"url": "https://ipinfo.io/json", "name": "ipinfo", "parser": lambda x: x["ip"]},
    {"url": "https://api.my-ip.io/ip.json", "name": "my-ip.io", "parser": lambda x: x["ip_address"]},
    {"url": "https://api.ip.sb/jsonip", "name": "ip.sb", "parser": lambda x: x["ip"]},
    {"url": "https://icanhazip.com", "name": "icanhazip", "parser": lambda x: x.strip()},
]
'''


# 读取配置文件
config = configparser.ConfigParser()
config.read("app/config.ini", encoding="utf-8")

# 解析APIS_URL部分
PUBLIC_IP_APIS = []
for key, value in config.items("APIS_URL"):
    url, name, parser_name = value.split(", ", 2)
    parser_expr = eval(parser_name)
    PUBLIC_IP_APIS.append({
        "url": url,
        "name": name,
        "parser": parser_expr
    })


# 请求超时时间（秒）
TIMEOUT = 10

def get_public_ip() -> Tuple[Optional[str], Optional[str]]:
    """
    通过多个第三方 API 获取公网 IP 地址
    
    Returns:
        Tuple[Optional[str], Optional[str]]: (IP地址, 服务名称)，如果失败则返回 (None, None)
    """
    for service in PUBLIC_IP_APIS:
        try:
            pass
            response = requests.get(service["url"], timeout=TIMEOUT)
            
            if response.status_code == 200:
                # 根据服务格式解析响应
                try:
                    if "json" in response.headers.get("Content-Type", ""):
                        data = response.json()
                    else:
                        data = response.text
                    
                    ip = service["parser"](data)
                    pass
                    return ip, service["name"]
                except (KeyError, json.JSONDecodeError, TypeError) as e:
                    pass
                pass
        
        except requests.RequestException as e:
            pass
    
    return None, None

def get_ip_with_retry(max_attempts: int = 3, delay: int = 2) -> Tuple[Optional[str], Optional[str]]:
    """
    带重试机制的公网 IP 获取
    
    Args:
        max_attempts: 最大尝试次数
        delay: 重试间隔（秒）
    
    Returns:
        Tuple[Optional[str], Optional[str]]: (IP地址, 服务名称)，如果失败则返回 (None, None)
    """
    for attempt in range(1, max_attempts + 1):
        ip, service = get_public_ip()
        
        if ip:
            return ip, service
        
        if attempt < max_attempts:
            time.sleep(delay)
    return None, None

def getip() -> None:
    start_time = time.time()
    
    ip, service = get_ip_with_retry()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    result = ip
    
    return json.dumps(result, indent=2, ensure_ascii=False)
