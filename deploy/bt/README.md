# 宝塔面板部署指南（当前仓库）

## 1) 目标环境

- 宝塔面板 7+
- Nginx 1.20+
- Node.js 18+
- Python 3.11+
- PM2 管理器

## 2) 当前仓库关键事实

- 默认分支：`master`
- 后端端口：`8000`
- 前端生产构建目录：`/www/pest-disease-detection/frontend/dist`
- 前端请求约定：`/api/*`，Nginx 需重写到后端 `/*`

## 3) 数据库与账号（按当前联调）

- 数据库：`corn`
- 用户：`appuser`
- 密码：`Gwrr76AhsSYwmhde`
- 主机：`139.129.37.65:3306`

如需改库名/账号，可在执行部署脚本时通过环境变量覆盖：

```bash
DB_NAME=xxx DB_USER=xxx DB_PASSWORD=xxx DB_HOST=xxx DB_PORT=xxx bash deploy/bt/deploy.sh
```

## 4) 一键部署

在服务器执行：

```bash
cd /www
git clone ssh://git@ssh.github.com:443/wjy20001122/pest-disease-detection.git
cd /www/pest-disease-detection
git checkout master
bash deploy/bt/deploy.sh
```

## 5) Nginx 配置

将 `deploy/bt/nginx.conf` 内容复制到宝塔站点配置并替换：

- `server_name` 改为你的域名
- 证书路径改为宝塔签发证书路径

配置已包含：

- `/api/* -> 后端 /*` 统一重写
- `/api/detection/camera/ws` WebSocket 透传
- `/socket.io/` WebSocket 透传

## 6) PM2 服务

部署脚本会加载：

`/www/pest-disease-detection/deploy/bt/ecosystem.config.json`

常用命令：

```bash
pm2 list
pm2 logs pdds-backend
pm2 restart pdds-backend
pm2 save
```

## 7) 部署后验收

```bash
curl -I http://127.0.0.1:8000/docs
curl -I http://127.0.0.1
```

浏览器侧重点验证：

- 登录/注册
- 检测页上传（原图+结果图）
- 跟踪页状态流转
- 通知已读与全部已读
- 管理后台（用户/通知/模型）

## 8) GitHub Actions 说明

- 当前 `deploy.yml` 监听 `master`
- `deploy-models` 仅在 `model-server/models/**` 存在时触发
- 若使用 Actions 部署，请先配置仓库 Secrets：
  - `SERVER_HOST`
  - `SERVER_USER`
  - `SERVER_PASSWORD`
  - `SERVER_PORT`
