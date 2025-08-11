# IP地址访问控制系统说明文档

## 项目概述

本项目是一个基于Docker的IP地址访问控制系统，主要用于限制对Web服务的访问，只允许特定IP地址访问。系统由Nginx和一个Webhook服务组成，当接收到新的IP地址时，会自动更新Nginx配置并重新加载，实现动态IP访问控制。

**重要特性：**
- 支持加密通信，确保IP地址传输安全
- 支持数字签名验证，防止数据篡改
- 向后兼容明文通信模式
- 防重放攻击机制

## 项目结构

```
accept_ip/
├── .env                 # 环境配置文件（包含加密密钥）
├── Dockerfile.nginx     # Nginx服务的Docker配置文件
├── Dockerfile.webhook   # Webhook服务的Docker配置文件
├── docker-compose.yml   # Docker服务编排文件
├── nginx.conf           # Nginx主配置文件
├── crypto_utils.py      # 加密通信工具类
├── requirements.txt     # Python依赖包列表
└── webhook.py           # Webhook服务实现
```

## 文件说明

### Dockerfile.nginx

用于构建Nginx服务的Docker镜像，基于nginx:alpine镜像。主要功能包括：
- 复制Nginx配置文件
- 创建初始的IP访问控制配置
- 创建简单的测试页面

### Dockerfile.webhook

用于构建Webhook服务的Docker镜像，基于python:3.9-alpine镜像。主要功能包括：
- 安装Python Flask框架和requests库
- 安装Docker客户端
- 配置Webhook服务启动命令

### docker-compose.yml

Docker服务编排文件，定义了两个服务：
1. nginx服务：
   - 使用Dockerfile.nginx构建
   - 映射80端口
   - 挂载配置文件卷

2. webhook服务：
   - 使用Dockerfile.webhook构建
   - 映射5000端口
   - 挂载配置文件卷和Docker套接字

### nginx.conf

Nginx主配置文件，关键配置包括：
- 配置真实IP识别
- 应用IP访问限制
- 包含允许的IP地址列表文件

### crypto_utils.py

加密通信工具类，提供以下功能：
- 数据加密/解密（使用Fernet对称加密）
- 数字签名生成/验证（使用HMAC-SHA256）
- 防重放攻击（时间戳验证）
- 密钥派生（使用PBKDF2）

### webhook.py

Webhook服务实现，主要功能包括：
- 接收Webhook请求并提取IP地址
- 支持加密和明文两种通信模式
- 验证数字签名确保数据完整性
- 更新Nginx配置文件
- 平滑重启Nginx服务

## 使用方法

1. 确保已安装Docker和Docker Compose
2. 在项目目录下执行以下命令启动服务：
   ```bash
   docker-compose up -d
   ```
3. 服务启动后，Nginx将在80端口监听，Webhook服务在5000端口监听
4. 向Webhook服务发送包含IP地址的请求，系统将自动更新Nginx配置并重新加载

## 配置说明

### IP地址管理
系统通过`/etc/nginx/conf.d/allowed_ips.conf`文件管理允许访问的IP地址列表。Webhook服务会自动更新此文件并重新加载Nginx配置。

### Webhook数据格式

#### 加密模式（推荐）
```json
{
  "encryption_enabled": true,
  "encrypted_data": "base64编码的加密数据",
  "signature": "HMAC-SHA256签名"
}
```

#### 明文模式（向后兼容）
```json
{
  "current_ip": "192.168.1.100",
  "previous_ip": "192.168.1.99",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 加密通信配置

在`.env`文件中配置加密密钥：
```
SECRET_KEY=your_secret_key_here
```

**注意：** 确保send_ip和accept_ip服务使用相同的SECRET_KEY。

## 注意事项

1. 确保Docker容器有权限访问Docker套接字
2. 根据实际环境调整Nginx配置中的`set_real_ip_from`参数
3. 建议在生产环境中使用HTTPS保护Webhook端点