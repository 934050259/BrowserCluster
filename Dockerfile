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
FROM python:3.10-slim

WORKDIR /app

# 安装Playwright所需的系统依赖
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
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*


# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai

ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
# Install Python dependencies with Chinese mirror
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN playwright install chromium

# Copy Project Files
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Copy Frontend Build Artifacts
COPY --from=frontend-builder /app/admin/dist ./static

# 创建日志目录
RUN mkdir -p logs

# Expose port
EXPOSE 8000



# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
