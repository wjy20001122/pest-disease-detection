#!/bin/bash
set -e

# 宝塔部署脚本
# 适用于 Ubuntu/CentOS + 宝塔面板

PROJECT_DIR="/www/pest-disease-detection"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
REPO_URL="${REPO_URL:-ssh://git@ssh.github.com:443/wjy20001122/pest-disease-detection.git}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-master}"
DB_NAME="${DB_NAME:-corn}"
DB_USER="${DB_USER:-appuser}"
DB_PASSWORD="${DB_PASSWORD:-Gwrr76AhsSYwmhde}"
DB_HOST="${DB_HOST:-139.129.37.65}"
DB_PORT="${DB_PORT:-3306}"

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
    git clone "$REPO_URL" $PROJECT_DIR
    cd $PROJECT_DIR
    git checkout "$DEPLOY_BRANCH"
else
    git fetch origin
    git checkout "$DEPLOY_BRANCH"
    git pull origin "$DEPLOY_BRANCH"
fi

# 创建数据库
echo "[3/7] 创建数据库..."
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';"
mysql -u root -p -e "ALTER USER '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%'; FLUSH PRIVILEGES;"
mysql -u root -p "$DB_NAME" < $PROJECT_DIR/scripts/init_db.sql

# 安装前端依赖
echo "[4/7] 安装前端依赖..."
cd $FRONTEND_DIR
npm ci

# 构建前端
echo "[5/7] 构建前端..."
npm run build

# 安装后端依赖
echo "[6/7] 安装后端依赖..."
cd $BACKEND_DIR
python3 -m pip install -r requirements.txt

# 初始化数据库
echo "[7/7] 初始化数据库..."
cd $PROJECT_DIR
python3 scripts/init_db.py

# 配置 PM2
echo "[8/8] 配置 PM2..."
pm2 startOrReload $PROJECT_DIR/deploy/bt/ecosystem.config.json --only pdds-backend
pm2 save

# 设置开机自启
pm2 startup

echo ""
echo "=========================================="
echo "  部署完成!"
echo "=========================================="
echo ""
echo "访问地址: https://your-domain"
echo "后端API: http://your-server-ip:8000"
echo "API文档: http://your-server-ip:8000/docs"
echo ""
echo "常用命令:"
echo "  pm2 logs pdds-backend    - 查看后端日志"
echo "  pm2 restart pdds-backend - 重启后端"
echo "  pm2 list                 - 查看进程状态"
