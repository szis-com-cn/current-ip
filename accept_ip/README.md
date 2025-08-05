# IP地址访问控制系统说明文档

## 项目概述

本项目是一个基于Docker的IP地址访问控制系统，主要用于限制对Web服务的访问，只允许特定IP地址访问。系统由Nginx和一个Webhook服务组成，当接收到新的IP地址时，会自动更新Nginx配置并重新加载，实现动态IP访问控制。

## 项目结构

```
accept_ip/
├── Dockerfile.nginx     # Nginx服务的Docker配置文件
├── Dockerfile.webhook   # Webhook服务的Docker配置文件
├── docker-compose.yml   # Docker服务编排文件
├── nginx.conf           # Nginx主配置文件
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

### webhook.py

Webhook服务实现，主要功能包括：
- 接收Webhook请求并提取IP地址
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
Webhook服务支持多种数据格式来提取IP地址：
- JSON格式，包含`current_ip`或`previous_ip`字段
- 包含IP地址的文本内容

## 注意事项

1. 确保Docker容器有权限访问Docker套接字
2. 根据实际环境调整Nginx配置中的`set_real_ip_from`参数
3. 建议在生产环境中使用HTTPS保护Webhook端点