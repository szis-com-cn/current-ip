#!/bin/bash

# 全局IP控制Nginx部署脚本
# 功能: 部署具有全局IP访问控制的Nginx网关

set -e

echo "🚀 开始部署全局IP控制Nginx网关..."

# 检查必要文件
if [ ! -f "nginx-data/allowed_ips.conf" ]; then
    echo "❌ 错误: nginx-data/allowed_ips.conf 文件不存在"
    exit 1
fi

if [ ! -f "nginx-global-config/nginx.conf" ]; then
    echo "❌ 错误: nginx-global-config/nginx.conf 文件不存在"
    exit 1
fi

if [ ! -f "nginx-global-config/default.conf" ]; then
    echo "❌ 错误: nginx-global-config/default.conf 文件不存在"
    exit 1
fi

echo "✅ 配置文件检查通过"

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose down 2>/dev/null || true

# 停止可能存在的全局nginx容器
echo "🛑 停止现有的全局Nginx容器..."
docker stop nginx-global-gateway 2>/dev/null || true
docker rm nginx-global-gateway 2>/dev/null || true

# 创建日志卷
echo "📁 创建日志卷..."
docker volume create nginx-global-logs 2>/dev/null || true

# 启动全局IP控制的Nginx
echo "🌐 启动全局IP控制Nginx网关..."
docker run -d \
  --name nginx-global-gateway \
  --restart unless-stopped \
  -p 80:80 \
  -p 443:443 \
  -v "$(pwd)/nginx-global-config/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$(pwd)/nginx-global-config/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$(pwd)/nginx-data/allowed_ips.conf:/etc/nginx/allowed_ips.conf:ro" \
  -v nginx-global-logs:/var/log/nginx \
  --add-host=host.docker.internal:host-gateway \
  nginx:alpine

echo "⏳ 等待Nginx启动..."
sleep 3

# 检查Nginx配置
echo "🔧 验证Nginx配置..."
if docker exec nginx-global-gateway nginx -t; then
    echo "✅ Nginx配置验证成功"
else
    echo "❌ Nginx配置验证失败"
    docker logs nginx-global-gateway
    exit 1
fi

# 重新启动webhook服务
echo "🔄 启动Webhook服务..."
docker-compose up -d

echo "⏳ 等待服务启动..."
sleep 5

# 测试服务
echo "🧪 测试服务状态..."

echo "测试健康检查端点:"
if curl -s http://localhost/health | jq . 2>/dev/null; then
    echo "✅ 健康检查端点正常"
else
    echo "⚠️  健康检查端点可能有问题，但服务可能仍在启动中"
fi

echo "测试根路径:"
if curl -s http://localhost/ | jq . 2>/dev/null; then
    echo "✅ 根路径访问正常"
else
    echo "⚠️  根路径访问可能有问题"
fi

echo ""
echo "🎉 部署完成！"
echo ""
echo "📊 服务状态:"
echo "- Nginx网关: http://localhost (端口80)"
echo "- 健康检查: http://localhost/health"
echo "- Webhook端点: http://localhost/webhook"
echo "- 服务器状态: http://localhost/nginx-status (仅管理员IP)"
echo ""
echo "📋 管理命令:"
echo "- 查看Nginx日志: docker logs nginx-global-gateway"
echo "- 查看访问日志: docker exec nginx-global-gateway tail -f /var/log/nginx/access.log"
echo "- 查看安全日志: docker exec nginx-global-gateway tail -f /var/log/nginx/security.log"
echo "- 重载配置: docker exec nginx-global-gateway nginx -s reload"
echo "- 停止服务: docker stop nginx-global-gateway && docker-compose down"
echo ""
echo "🛡️  安全提醒:"
echo "- 当前IP白名单文件: nginx-data/allowed_ips.conf"
echo "- 修改白名单后需要重载: docker exec nginx-global-gateway nginx -s reload"
echo "- 确保您的IP在白名单中，避免被锁定"
echo ""
echo "✨ 全局IP控制已启用，只有白名单中的IP可以访问服务器！"