# 宝塔面板部署指南

## 环境要求

- 宝塔面板 7.0+
- Nginx 1.20+
- Node.js 18+ (通过宝塔软件商店安装)
- Python 3.11+ (通过宝塔Python项目管理器)
- MySQL 8.0+ (通过宝塔软件商店安装)
- Redis 6+ (通过宝塔软件商店安装)
- PM2管理器 (通过宝塔软件商店安装)

## 阿里云 OSS 准备

1. 登录阿里云控制台，开通对象存储 OSS
2. 创建存储桶，记下：
   - Endpoint（如：oss-cn-hangzhou.aliyuncs.com）
   - AccessKey ID 和 AccessKey Secret
3. 创建存储桶，名称如 `pdds-files`

## 部署步骤

### 1. 服务器环境准备

在宝塔面板的软件商店中安装以下软件：

| 软件 | 版本 | 用途 |
|------|------|------|
| Nginx | 1.20+ | Web服务器/反向代理 |
| Node.js | 18 LTS | 运行前端 |
| Python | 3.11 | 运行后端 |
| MySQL | 8.0+ | 主数据库 |
| Redis | 6+ | 缓存/消息队列 |
| PM2管理器 | 最新 | Node进程管理 |

### 2. 创建数据库

在宝塔面板的数据库管理中创建：

```
数据库名: pdds
用户名: pddsuser
密码: pddspass (请修改为强密码)
编码: utf8mb4
```

### 3. 上传代码

方式一：Git 克隆
```bash
cd /www
git clone git@github.com:your-org/pest-disease-detection.git
```

方式二：直接上传压缩包到 /www/pest-disease-detection

### 4. 修改配置文件

编辑 `backend/app/core/config.py` 或设置环境变量：

```python
DATABASE_URL = "mysql+aiomysql://pddsuser:你的密码@localhost:3306/pdds?charset=utf8mb4"

# 阿里云 OSS 配置
OSS_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
OSS_ACCESS_KEY_ID = "你的AccessKeyID"
OSS_ACCESS_KEY_SECRET = "你的AccessKeySecret"
OSS_BUCKET = "pdds-files"
```

### 5. 安装依赖并构建

```bash
cd /www/pest-disease-detection/frontend
npm install
npm run build

cd /www/pest-disease-detection/backend
pip install -r requirements.txt
```

### 6. 配置 Nginx

在宝塔面板中创建网站，复制 `deploy/bt/nginx.conf` 中的配置到网站设置。

**注意**：请修改 `server_name` 为你的域名，并将 SSL 证书路径改为宝塔自动生成的路径。

### 7. 配置 PM2

```bash
cd /www/pest-disease-detection
pm2 start deploy/bt/ecosystem.config.json
pm2 save
pm2 startup
```

### 8. 配置 GitHub Actions 自动部署

在 GitHub 仓库的 Settings -> Secrets 中添加：

| Secret 名称 | 说明 |
|-------------|------|
| SERVER_HOST | 服务器 IP 地址 |
| SERVER_USER | SSH 用户名 |
| SERVER_PASSWORD | SSH 密码 |
| SERVER_PORT | SSH 端口 (默认22) |

## 目录结构

```
/www/pest-disease-detection/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── core/        # 核心配置
│   │   ├── models/      # 数据模型
│   │   └── schemas/     # Pydantic schemas
│   ├── main.py          # 入口文件
│   └── requirements.txt
│
├── frontend/             # Vue3 前端
│   ├── dist/            # 构建产物 (Nginx root)
│   ├── src/             # 源代码
│   └── package.json
│
└── deploy/
    └── bt/              # 宝塔部署配置
        ├── nginx.conf
        ├── ecosystem.config.json
        └── deploy.sh
```

## 常用命令

```bash
# 查看日志
pm2 logs pdds-backend

# 重启服务
pm2 restart pdds-backend

# 查看状态
pm2 list

# 更新代码后重载
cd /www/pest-disease-detection && git pull && pm2 restart pdds-backend
```

## HTTPS 配置

1. 在宝塔面板中为网站申请 Let's Encrypt 免费证书
2. 或上传自己的 SSL 证书
3. 确保证书路径在 nginx.conf 中正确配置

## 故障排查

### 后端无法启动

```bash
# 查看错误日志
pm2 logs pdds-backend --err

# 手动测试
cd /www/pest-disease-detection/backend
python main.py
```

### 数据库连接失败

检查 MySQL 服务状态和防火墙设置：

```bash
systemctl status mysqld
firewall-cmd --list-ports
```

### 前端资源404

确保 Nginx 的 `root` 路径指向 `frontend/dist` 目录：
```nginx
root /www/pest-disease-detection/frontend/dist;
```
