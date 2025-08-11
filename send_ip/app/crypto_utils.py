import base64
import hashlib
import hmac
import json
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class CryptoManager:
    """加密通信管理器"""
    
    def __init__(self, secret_key: str):
        """
        初始化加密管理器
        
        Args:
            secret_key (str): 用于加密的密钥
        """
        self.secret_key = secret_key.encode()
        self.fernet = self._generate_fernet()
    
    def _generate_fernet(self):
        """基于密钥生成Fernet加密器"""
        # 使用PBKDF2从密钥生成32字节的密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'current_ip_salt',  # 固定盐值，确保相同密钥生成相同的加密器
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
        return Fernet(key)
    
    def encrypt_data(self, data: dict) -> str:
        """
        加密数据
        
        Args:
            data (dict): 要加密的数据
            
        Returns:
            str: 加密后的base64编码字符串
        """
        # 添加时间戳防止重放攻击
        data['timestamp'] = int(time.time())
        
        # 将数据转换为JSON字符串
        json_data = json.dumps(data, ensure_ascii=False)
        
        # 加密数据
        encrypted_data = self.fernet.encrypt(json_data.encode('utf-8'))
        
        # 返回base64编码的加密数据
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str, max_age: int = 300) -> dict:
        """
        解密数据
        
        Args:
            encrypted_data (str): 加密的base64编码字符串
            max_age (int): 最大允许的时间差（秒），防止重放攻击
            
        Returns:
            dict: 解密后的数据
            
        Raises:
            ValueError: 解密失败或数据过期
        """
        try:
            # 解码base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # 解密数据
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            
            # 转换为JSON
            json_data = decrypted_bytes.decode('utf-8')
            data = json.loads(json_data)
            
            # 检查时间戳，防止重放攻击
            if 'timestamp' in data:
                current_time = int(time.time())
                data_time = data['timestamp']
                if current_time - data_time > max_age:
                    raise ValueError(f"数据过期，时间差: {current_time - data_time}秒")
            
            return data
            
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")
    
    def generate_signature(self, data: str) -> str:
        """
        生成数据签名
        
        Args:
            data (str): 要签名的数据
            
        Returns:
            str: 签名的十六进制字符串
        """
        signature = hmac.new(
            self.secret_key,
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, data: str, signature: str) -> bool:
        """
        验证数据签名
        
        Args:
            data (str): 原始数据
            signature (str): 签名
            
        Returns:
            bool: 签名是否有效
        """
        expected_signature = self.generate_signature(data)
        return hmac.compare_digest(expected_signature, signature)