# 使用Python 3.12作为基础镜像
FROM python:3.12

# 设置工作目录
WORKDIR /app

# 复制项目文件到工作目录
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动应用程序
CMD ["python", "app/main.py"]
