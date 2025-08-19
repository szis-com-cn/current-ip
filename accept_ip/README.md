# IP地址访问控制系统说明文档

## 项目概述

本项目是一个基于Docker的IP地址访问控制系统，主要用于动态限制对Web服务的访问，只允许特定IP地址访问。系统由Nginx和一个Webhook服务组成，当接收到新的IP地址时，会自动更新Nginx配置并重新加载，实现动态IP访问控制。

**重要特性：**

- 支持加密通信，确保IP地址传输安全
- 支持数字签名验证，防止数据篡改
- 向后兼容明文通信模式
- 防重放攻击机制
- 统一密钥策略：同一密钥用于加密与API请求头校验
- 动态IP白名单管理与Nginx平滑重载

## 项目结构

```
current-ip/
├── accept_ip/          # 接收端（IP访问控制服务）
│   ├── .env           # 环境配置文件（包含统一密钥）
│   ├── docker-compose.yml  # Docker服务编排文件
│   ├── nginx.conf     # Nginx主配置文件
│   ├── webhook.py     # Webhook服务实现
│   ├── crypto_utils.py  # 加密通信工具类
│   └── logs/          # 日志文件目录
└── send_ip/           # 发送端（IP变动检测与通知）
    ├── .env           # 环境配置文件
    ├── docker-compose.yml
    ├── app/           # 应用代码目录
    └── logs/          # 日志文件目录
```

## 手动测试全流程（新手友好）

### 一、准备工作

1) 安装 Docker 与 Docker Compose（Mac/Windows 可用 Docker Desktop）
2) 克隆或下载本项目代码，终端进入 current-ip 目录
3) 确认目录结构：accept_ip（接收端）、send_ip（发送端）

### 二、配置

**A. 接收端 accept_ip/.env**

- `CRYPTO_SECRET_KEY=你的统一密钥` （同一个密钥将用于加密与请求头 X-API-Key）
- 其余日志配置可保持默认：`LOG_FILE=/app/logs/webhook.log`

**B. 发送端 send_ip/.env**

- `[webhook]`
  - `webhook1 = http://host.docker.internal:5000/webhook` （Docker Desktop 场景下）
  - `secret_key = 与接收端相同的统一密钥`
- `[time]`
  - `sleeptime = 10` （循环间隔秒）

### 三、启动服务

1) 启动接收端（accept_ip）：
   ```bash
   cd accept_ip && docker compose up -d --build
   ```
2) 启动发送端（send_ip）：
   ```bash
   cd ../send_ip && docker compose up -d --build
   ```

### 四、验证连通性（无需进入容器）

1) 宿主机测试接收端健康检查：

   ```bash
   curl http://localhost:5000/health
   ```

   预期：返回 200 OK
2) 宿主机发送一次明文连接测试（含统一密钥头）：

   ```bash
   curl -i -H 'Content-Type: application/json' -H 'X-API-Key: 你的统一密钥' \
        -d '{"type":"connection_test","message":"ping","encryption_enabled":false}' \
        http://localhost:5000/webhook
   ```

   预期：返回 200 OK

### 五、IP访问控制功能测试

**注意：** 接收端Nginx运行在端口88（http://localhost:88），端口5000只用于Webhook通信。

1) **测试初始拒绝状态**：

   ```bash
   curl -i http://localhost:88/
   ```

   预期：返回 404 Not Found（因为IP不在白名单中）
2) **通过Webhook添加当前IP到白名单**：

   ```bash
   curl -i -H 'Content-Type: application/json' -H 'X-API-Key: 你的统一密钥' \
        -d '{"current_ip":"192.168.65.1","timestamp":"2025-08-14T12:00:00"}' \
        http://localhost:5000/webhook
   ```

   预期：返回 200 OK，日志显示"已更新Nginx配置文件"
3) **验证IP白名单生效**：

   ```bash
   curl -i http://localhost:88/
   ```

   预期：返回 200 OK，显示"IP Access Control System"页面
4) **查看当前白名单配置**：

   ```bash
   cat accept_ip/nginx-data/allowed_ips.conf
   ```

   应该看到类似：

   ```
   # 允许访问的IP地址列表
   allow xxx.xxx.xxx.xxx;
   deny all;
   ```
5) **测试重置白名单（模拟移除访问权限）**：

   ```bash
   printf "# 允许访问的IP地址列表\ndeny all;\n" > accept_ip/nginx-data/allowed_ips.conf
   docker restart ip-nginx-1
   sleep 3
   curl -i http://localhost:88/
   ```

   预期：再次返回 404 Not Found

### 六、查看日志（无需进入容器）

- 接收端日志：`tail -f accept_ip/logs/webhook.log`
- 发送端日志：`tail -f send_ip/logs/app.log`

### 七、触发真实发送与Nginx自动更新

1) 等待发送端检测到IP变更或直接修改 `send_ip/ip.txt`内容以模拟变更：

   ```bash
   echo "203.0.113.100" > send_ip/ip.txt
   ```
2) 观察日志：

   - 发送端 `send_ip/logs/app.log`：应看到"使用加密模式发送Webhook数据（含X-API-Key）""Webhook发送响应 - 状态卡: 200"
   - 接收端 `accept_ip/logs/webhook.log`：应看到"API Key 验证成功""成功解密Webhook数据""提取到IP地址: x.x.x.x""Nginx配置已更新并成功重启"

### 八、完整的加密通信测试

发送端会自动使用加密模式发送数据，也可以手动测试加密通信：

```bash
# 注意：加密数据需要使用专门的工具生成，这里仅演示格式
curl -i -H 'Content-Type: application/json' -H 'X-API-Key: 你的统一密钥' \
     -d '{"encryption_enabled":true,"encrypted_data":"base64编码的加密数据","signature":"HMAC签名"}' \
     http://localhost:5000/webhook
```

### 九、常见问题与故障排除

**curl命令错误修正**：
原命令（错误）：

```bash
curl -i -H 'Content-Type: application/json' -H 'X-API-Key: test_secret_key_123456'                                                                                               
-d '{"type":"connection_test","message":"ping","encryption_enabled":false}'                                 
http://localhost:5000/webhook
```

正确命令：

```bash
curl -i -H 'Content-Type: application/json' -H 'X-API-Key: test_secret_key_123456' \
     -d '{"type":"connection_test","message":"ping","encryption_enabled":false}' \
     http://localhost:5000/webhook
```

**常见错误解决**：

- **403 Forbidden**：检查两端密钥是否一致；检查请求是否包含 X-API-Key；接收端 .env 是否设置了 CRYPTO_SECRET_KEY
- **连接失败**：发送端 webhook1 地址推荐使用 `http://host.docker.internal:5000/webhook`（Docker Desktop）。Linux 原生 Docker 环境可直接使用宿主机 IP:5000
- **解密失败**：两端统一密钥不一致导致；或发送端未开启加密却附带加密标识
- **404 Not Found**：正常现象，表示IP不在白名单中，需要通过Webhook添加IP到白名单

### 十、环境重置

若需要重置环境，可在 accept_ip 与 send_ip 目录分别执行：

```bash
docker compose down -v && docker compose up -d --build
```

## 数据格式说明

### Webhook数据格式

**加密模式（推荐）**：

```json
{
  "encryption_enabled": true,
  "encrypted_data": "base64编码的加密数据",
  "signature": "HMAC-SHA256签名"
}
```

**明文模式（向后兼容）**：

```json
{
  "current_ip": "192.168.1.100",
  "previous_ip": "192.168.1.99", 
  "timestamp": "2024-01-01T12:00:00"
}
```

**连接测试格式**：

```json
{
  "type": "connection_test",
  "message": "ping",
  "encryption_enabled": false
}
```

## 安全配置

1. **统一密钥管理**：确保 `accept_ip/.env` 中的 `CRYPTO_SECRET_KEY` 与 `send_ip/.env` 中的 `secret_key` 保持一致
2. **API请求头校验**：系统自动使用 `X-API-Key` 头进行身份验证
3. **加密通信**：生产环境强烈建议使用加密模式传输敏感IP数据
4. **日志安全**：日志文件包含操作记录但不记录完整密钥信息

## 注意事项

1. 确保Docker容器有权限访问Docker套接字
2. 根据实际环境调整Nginx配置中的 `set_real_ip_from`参数
3. 建议在生产环境中使用HTTPS保护Webhook端点
4. IP白名单仅对根路径（`/`）生效，其他静态资源路径不受限制
5. 更换统一密钥时需同步修改两端配置文件并重启服务
