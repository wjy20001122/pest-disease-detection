#!/bin/bash
set -e

# 宝塔部署脚本
# 适用于 Ubuntu/CentOS + 宝塔面板

PROJECT_DIR="/www/pest-disease-detection"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=========================================="
echo "  病虫害检测系统 - 宝塔一键部署"
echo "=========================================="

# 创建项目目录
echo "[1/7] 创建项目目录..."
sudo mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 克隆/更新代码
echo "[2/7] 拉取最新代码..."
if [ ! -d ".git" ]; then
    git clone git@github.com:your-org/pest-disease-detection.git $PROJECT_DIR
else
    git pull origin main
fi

# 创建数据库
echo "[3/7] 创建数据库..."
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS pdds CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p pdds < $PROJECT_DIR/scripts/init_db.sql

# 安装前端依赖
echo "[4/7] 安装前端依赖..."
cd $FRONTEND_DIR
npm install

# 构建前端
echo "[5/7] 构建前端..."
npm run build

# 安装后端依赖
echo "[6/7] 安装后端依赖..."
cd $BACKEND_DIR
pip install -r requirements.txt

# 初始化数据库
echo "[7/7] 初始化数据库..."
cd $PROJECT_DIR
python scripts/init_db.py

# 配置 PM2
echo "[8/8] 配置 PM2..."
pm2 delete pdds-backend 2>/dev/null || true
pm2 start $PROJECT_DIR/deploy/bt/ecosystem.config.json
pm2 save

# 设置开机自启
pm2 startup

echo ""
echo "=========================================="
echo "  部署完成!"
echo "=========================================="
echo ""
echo "访问地址: http://your-server-ip:3000"
echo "后端API: http://your-server-ip:8000"
echo "API文档: http://your-server-ip:8000/docs"
echo ""
echo "默认管理员账户:"
echo "  用户名: admin"
echo "  密码: admin123"
echo ""
echo "常用命令:"
echo "  pm2 logs pdds-backend    - 查看后端日志"
echo "  pm2 restart pdds-backend - 重启后端"
echo "  pm2 list                 - 查看进程状态"
