# Build Stage for Frontend
FROM node:22-alpine as frontend-builder

WORKDIR /app/admin

# Copy package files
COPY admin/package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY admin/ .

# Build frontend
RUN npm run build

# Runtime Stage for Backend
FROM python:3.10

WORKDIR /app

# 安装 Playwright 和 DrissionPage (Chromium) 所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    tzdata \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    libxml2 \
    libxslt1.1 \
    chromium \
    # 补充 DrissionPage 运行可能需要的额外依赖 (如显示驱动支持)
    libxss1 \
    libappindicator3-1 \
    libsecret-1-0 \
    lsb-release \
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*


# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
# 安装 Python dependencies with Chinese mirror
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN playwright install --with-deps chromium && \
    if [ -f /usr/bin/chromium ]; then ln -s /usr/bin/chromium /usr/bin/google-chrome || true; fi
# 安装 DrissionPage 所需的浏览器 (如果需要独立安装，DrissionPage 默认可使用系统或 Playwright 安装的 Chromium)
# 为确保隔离和路径正确，我们也可以显式指定一些环境参数
ENV DRISSIONPAGE_RETRY_TIMES=3 \
    DRISSIONPAGE_TIMEOUT=30

# Copy Project Files
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY .env.example .

# Copy Frontend Build Artifacts
COPY --from=frontend-builder /app/admin/dist ./static

# 创建日志目录
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# 启动时依次执行：
# 1. 如果 .env 不存在且没有设置关键环境变量 (MONGO_URI, REDIS_URL, REDIS_CACHE_URL, RABBITMQ_URL)，则从 .env.example 复制
# 2. 数据库初始化、配置初始化、账号初始化
# 3. 启动应用
CMD if [ ! -f .env ] && [ -z "$MONGO_URI" ] && [ -z "$REDIS_URL" ] && [ -z "$REDIS_CACHE_URL" ] && [ -z "$RABBITMQ_URL" ]; then cp .env.example .env; fi && \
    python scripts/init_db.py && \
    python scripts/init_configs_db.py && \
    python scripts/init_admin.py && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000
