# [SZIS-EDU-202507-002 服务器公网IP变动通知](./SZIS-EDU-202507-002%20服务器公网IP变动通知.md)

- [MIT License](./LICENSE.md)
- [新思开源](https://gitea.szis.dev/szisos/current-ip)
- [Github](https://github.com/szis-com-cn/current-ip)
- [Gitee](https://gitee.com/szis-os/current-ip)

# 服务器公网IP变动通知服务

## 项目概述
本项目旨在开发一个轻量级的后台服务，用于自动监测本机公网IP变化，并通过多种渠道（邮件、飞书、钉钉）实时通知相关人员。同时，对外提供一个简单的API接口，以便其他内部系统可以按需查询该服务器的当前公网IP。

## 配置步骤
1. 复制 `.env_example` 为 `.env`。
2. 根据实际情况修改 `.env` 中的配置项，包括IP检查间隔、API服务端口、API访问Token、各通知渠道的配置信息等。

## 部署步骤
1. 确保已经安装了Docker和Docker Compose。
2. 在项目根目录下执行以下命令构建并启动容器：
   ```bash
   docker-compose up -d
   ```