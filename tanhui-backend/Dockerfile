# syntax=docker/dockerfile:1
# ============ 碳惠陇原统一后端镜像 ============
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/app

# 依赖层（利用缓存）
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# 应用代码
COPY . .

# 迁移 + 启动（首次部署由 compose 的 init 任务执行 alembic upgrade head）
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
