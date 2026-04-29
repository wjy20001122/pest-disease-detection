# -*- coding: utf-8 -*-
# @Time : 2026-04-09
# @Author : 魏继勇
# 阿里云OSS配置

import os

# ==================== 阿里云OSS配置 ====================
OSS_ACCESS_KEY_ID = os.environ.get('OSS_ACCESS_KEY_ID', 'YOUR_ACCESS_KEY_ID').strip()
OSS_ACCESS_KEY_SECRET = os.environ.get('OSS_ACCESS_KEY_SECRET', 'YOUR_ACCESS_KEY_SECRET').strip()
OSS_ENDPOINT = os.environ.get('OSS_ENDPOINT', 'oss-cn-qingdao.aliyuncs.com').strip()
OSS_BUCKET_NAME = os.environ.get('OSS_BUCKET_NAME', 'corpdisease').strip()
OSS_DOMAIN = os.environ.get('OSS_DOMAIN', '').strip()

# 存储路径配置
OSS_BASE_PATH = 'corn-disease-detection'
OSS_IMG_PATH = f'{OSS_BASE_PATH}/images'
OSS_VIDEO_PATH = f'{OSS_BASE_PATH}/videos'
OSS_CAMERA_PATH = f'{OSS_BASE_PATH}/camera'
OSS_AVATAR = f'{OSS_BASE_PATH}/avatars'

# 启用OSS存储（所有文件只存储到OSS）
USE_OSS = True
