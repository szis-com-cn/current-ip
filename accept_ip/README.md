# IP地址访问控制系统 (accept_ip)

[![Docker](https://img.shields.io/badge/Docker-Supported-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🚀 项目概述

`accept_ip` 是一个高效的基于 Docker 的 IP 地址访问控制系统，专为动态 Web 服务访问管理而设计。系统通过 Webhook 接口接收 IP 变更通知，自动更新 Nginx 白名单配置，实现实时的访问控制管理。

### ✨ 核心特性

- 🔄 **动态 IP 管理**：实时接收和处理 IP 变更请求
- 🛡️ **安全访问控制**：基于 IP 白名单的精确访问控制
- 🔧 **外部 Nginx 集成**：支持与外部 Nginx 服务无缝集成
- 📝 **详细日志记录**：完整的操作日志和错误追踪
- 🚫 **防重放攻击**：内置时间戳验证机制
- 🐳 **容器化部署**：完全基于 Docker 的轻量级部署
- 🔍 **健康检查**：内置服务健康监控端点
- 📊 **RESTful API**：标准化的 HTTP API 接口

### 🏗️ 系统架构

```
┌─────────────────┐    HTTP POST     ┌──────────────────┐    文件写入    ┌─────────────────┐
│   send_ip       │ ──────────────▶ │   accept_ip      │ ──────────▶ │  Nginx 配置     │
│  (IP检测服务)   │   /webhook       │  (接收处理服务)  │             │ allowed_ips.conf│
└─────────────────┘                  └──────────────────┘             └─────────────────┘
                                              │                                │
                                              ▼                                ▼
                                     ┌──────────────────┐             ┌─────────────────┐
                                     │   日志记录       │             │  外部 Nginx     │
                                     │  webhook.log     │             │  (访问控制)     │
                                     └──────────────────┘             └─────────────────┘
```

## 📁 项目结构

```
accept_ip/
├── .env                    # 环境配置文件
├── docker-compose.yml      # Docker 服务编排配置
├── Dockerfile.webhook      # Webhook 服务镜像构建文件
├── webhook.py              # 核心 Webhook 服务实现
├── requirements.txt        # Python 依赖包列表
├── README.md              # 项目说明文档
├── logs/                  # 运行日志目录
│   └── webhook.log        # Webhook 服务日志
└── nginx-data/            # Nginx 配置数据目录
    └── allowed_ips.conf   # 动态生成的 IP 白名单配置
```

### 📋 文件说明

| 文件/目录 | 说明 |
|-----------|------|
| `webhook.py` | 核心服务文件，处理 IP 变更请求和配置更新 |
| `.env` | 环境变量配置，包含 Nginx 路径和重载方式设置 |
| `docker-compose.yml` | Docker 容器编排配置，定义服务启动参数 |
| `Dockerfile.webhook` | 用于构建独立 webhook 服务镜像 |
| `nginx-data/` | 与外部 Nginx 共享的配置目录 |
| `logs/` | 服务运行日志存储目录 |

## 🚀 快速开始

### 📋 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 外部 Nginx 服务（可选，用于生产环境）

### ⚙️ 环境配置

#### 1. 基础配置

复制并编辑环境配置文件：

```bash
cp .env.example .env
```

#### 2. 配置 `.env` 文件

```bash
# Nginx配置路径（容器内路径）
NGINX_CONFIG_PATH=/etc/nginx/conf.d/allowed_ips.conf

# Nginx重载方式：external（外部Nginx）或 internal（容器内Nginx）
NGINX_RELOAD_METHOD=external

# 服务端口
WEBHOOK_PORT=5000

# 日志配置
LOG_FILE=/app/logs/webhook.log
LOG_LEVEL=INFO
```

#### 3. 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `NGINX_CONFIG_PATH` | Nginx 配置文件路径 | `/etc/nginx/conf.d/allowed_ips.conf` |
| `NGINX_RELOAD_METHOD` | Nginx 重载方式 | `external` |
| `WEBHOOK_PORT` | Webhook 服务端口 | `5000` |
| `LOG_FILE` | 日志文件路径 | `/app/logs/webhook.log` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

> 💡 **提示**：`external` 模式下，系统仅更新配置文件，不执行 Nginx 重载。需要在外部 Nginx 配置中 `include` 生成的配置文件。

### 🏃‍♂️ 启动服务

#### 1. 构建并启动服务

```bash
# 启动 accept_ip 服务
cd accept_ip
docker-compose up -d --build
```

#### 2. 验证服务状态

```bash
# 检查容器状态
docker-compose ps

# 查看服务日志
docker-compose logs -f webhook

# 健康检查
curl http://localhost:5000/health
```

**预期响应**：
```json
{
  "status": "healthy",
  "service": "accept_ip webhook",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

## 🧪 API 文档

### 📡 健康检查接口

**GET** `/health`

检查服务运行状态。

**响应示例**：
```json
{
  "status": "healthy",
  "service": "accept_ip webhook",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

### 📨 Webhook 接口

**POST** `/webhook`

接收 IP 地址更新请求。

**请求格式**：
```json
{
  "current_ip": "192.168.1.100",
  "previous_ip": "192.168.1.99",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

**响应示例**：
```json
{
  "status": "success",
  "message": "IP address updated successfully",
  "ip": "192.168.1.100",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

### 🔧 连接测试接口

**POST** `/webhook`

用于测试 Webhook 连接性。

**请求格式**：
```json
{
  "type": "connection_test",
  "message": "ping"
}
```

**响应示例**：
```json
{
  "status": "success",
  "message": "Connection test successful"
}
```

## 🧪 测试示例

### 1. 连接测试

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "connection_test",
    "message": "ping"
  }'
```

### 2. IP 更新测试

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "current_ip": "192.168.1.100",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'" 
  }'
```

### 3. 配置验证

```bash
# 查看生成的 Nginx 配置
cat nginx-data/allowed_ips.conf

# 实时查看日志
tail -f logs/webhook.log

# 检查配置文件更新时间
ls -la nginx-data/allowed_ips.conf
```

**预期配置文件内容**：
```nginx
# 允许访问的IP地址列表
# 更新时间: 2024-01-20 10:30:00
allow 192.168.1.100;
deny all;
```

## 🔧 外部 Nginx 集成

### 配置示例

本系统支持与外部 Nginx 服务集成。Webhook 服务会生成 IP 白名单配置文件，外部 Nginx 可以通过 `include` 指令引入：

```nginx
server {
    listen 80;
    server_name example.com;
    
    location / {
        # 引入动态生成的 IP 白名单配置
        include /path/to/accept_ip/nginx-data/allowed_ips.conf;
        
        # 反向代理到后端服务
        proxy_pass http://backend_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Docker 卷挂载

如果使用 Docker 部署外部 Nginx，可以通过卷挂载共享配置文件：

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./accept_ip/nginx-data:/etc/nginx/conf.d/dynamic
    restart: unless-stopped
```

## 📊 日志管理

### 查看日志

```bash
# 实时查看 Webhook 服务日志
tail -f logs/webhook.log

# 查看 Docker 容器日志
docker-compose logs -f webhook

# 查看最近 100 行日志
tail -n 100 logs/webhook.log
```

### 日志格式

```
2024-01-20 10:30:00,123 - INFO - 接收到 Webhook 请求
2024-01-20 10:30:00,124 - INFO - 提取到IP地址: 192.168.1.100
2024-01-20 10:30:00,125 - INFO - 使用外部Nginx，配置已更新（未在容器内执行重载）
2024-01-20 10:30:00,126 - INFO - IP地址更新成功
```

## 🔧 故障排除

### 常见问题

#### 1. 服务无法启动

**问题**：容器启动失败

**解决方案**：
```bash
# 检查端口占用
lsof -i :5000

# 检查 Docker 日志
docker-compose logs webhook

# 重新构建镜像
docker-compose up -d --build --force-recreate
```

#### 2. 配置文件未更新

**问题**：IP 更新后配置文件没有变化

**解决方案**：
```bash
# 检查目录权限
ls -la nginx-data/

# 检查环境变量配置
cat .env

# 查看详细日志
docker-compose logs -f webhook
```

#### 3. 外部 Nginx 无法访问配置文件

**问题**：外部 Nginx 报告配置文件不存在

**解决方案**：
```bash
# 检查文件路径
ls -la nginx-data/allowed_ips.conf

# 检查文件权限
chmod 644 nginx-data/allowed_ips.conf

# 验证 Nginx 配置
nginx -t
```

### 调试模式

启用详细日志记录：

```bash
# 修改 .env 文件
LOG_LEVEL=DEBUG

# 重启服务
docker-compose restart webhook
```

### 环境重置

完全重置环境：

```bash
# 停止并删除所有容器和卷
docker-compose down -v

# 清理镜像（可选）
docker-compose down --rmi all

# 重新构建和启动
docker-compose up -d --build
```

## 📋 数据格式规范

### Webhook 请求格式

#### IP 更新请求

```json
{
  "current_ip": "192.168.1.100",
  "previous_ip": "192.168.1.99",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `current_ip` | string | ✅ | 当前 IP 地址 |
| `previous_ip` | string | ❌ | 之前的 IP 地址（可选） |
| `timestamp` | string | ✅ | ISO 8601 格式的时间戳 |

#### 连接测试请求

```json
{
  "type": "connection_test",
  "message": "ping"
}
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `type` | string | ✅ | 请求类型，固定值 `connection_test` |
| `message` | string | ✅ | 测试消息，通常为 `ping` |

### 响应格式

#### 成功响应

```json
{
  "status": "success",
  "message": "IP address updated successfully",
  "ip": "192.168.1.100",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### 错误响应

```json
{
  "status": "error",
  "message": "Invalid IP address format",
  "error_code": "INVALID_IP",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

## 🔒 安全注意事项

### 生产环境建议

1. **HTTPS 加密**：在生产环境中使用 HTTPS 保护 Webhook 端点
2. **访问控制**：限制 Webhook 端点的访问来源
3. **身份验证**：考虑添加 API 密钥或签名验证
4. **速率限制**：实施请求频率限制防止滥用
5. **日志监控**：定期检查日志文件，监控异常活动

### 网络安全

```nginx
# 示例：限制 Webhook 端点访问
location /webhook {
    # 仅允许特定 IP 访问
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    
    proxy_pass http://accept_ip_service;
}
```

### 文件权限

```bash
# 设置适当的文件权限
chmod 644 nginx-data/allowed_ips.conf
chmod 755 nginx-data/
chmod 644 logs/webhook.log
```

## 📚 相关文档

- [Nginx 启动配置指南](nginx/NGINX_STARTUP_GUIDE.md)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [Nginx 配置参考](https://nginx.org/en/docs/)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

**注意**：本文档持续更新中，如有疑问请查看最新版本或提交 Issue。
