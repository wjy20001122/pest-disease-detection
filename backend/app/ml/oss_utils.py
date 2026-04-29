# -*- coding: utf-8 -*-
# @Time : 2026-04-10
# @Author : 魏继勇
# OSS工具类

import os
import uuid
import time
import oss2
from .oss_confg import (
    OSS_ACCESS_KEY_ID,
    OSS_ACCESS_KEY_SECRET,
    OSS_ENDPOINT,
    OSS_BUCKET_NAME,
    OSS_DOMAIN,
    OSS_IMG_PATH,
    OSS_VIDEO_PATH,
    OSS_CAMERA_PATH,
    OSS_AVATAR,
    USE_OSS
)


class OSSUploader:
    """阿里云OSS文件上传工具类"""
    
    _instance = None
    _bucket = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_oss()
        return cls._instance
    
    def _init_oss(self):
        """初始化OSS连接"""
        if not USE_OSS:
            print("[WARN] OSS未启用，文件将保存到本地")
            return
        
        try:
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
            self._bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
            print(f"[INFO] OSS初始化成功: {OSS_BUCKET_NAME}")
        except Exception as e:
            print(f"[ERROR] OSS初始化失败: {str(e)}")
            self._bucket = None
    
    def _get_oss_path(self, category):
        """根据分类获取OSS存储路径"""
        path_map = {
            'img_predict': OSS_IMG_PATH,
            'video_predict': OSS_VIDEO_PATH,
            'camera_predict': OSS_CAMERA_PATH,
            'avatar': OSS_AVATAR
        }
        return path_map.get(category, OSS_IMG_PATH)
    
    def upload_file(self, file_path_or_array, category='img_predict', custom_filename=None):
        """
        上传文件到OSS

        Args:
            file_path_or_array: 本地文件路径或numpy数组
            category: 文件分类 (img_predict, video_predict, camera_predict, data_collection, avatar)
            custom_filename: 自定义文件名，如果不提供则自动生成

        Returns:
            str: OSS文件URL，失败返回None
        """
        if not USE_OSS or not self._bucket:
            print("[WARN] OSS未启用或未初始化，无法上传文件")
            return None

        temp_file = None
        try:
            if isinstance(file_path_or_array, str):
                file_path = file_path_or_array
                if not os.path.exists(file_path):
                    print(f"[ERROR] 文件不存在: {file_path}")
                    return None
            else:
                import numpy as np
                import cv2
                frame = file_path_or_array
                temp_file = f"./temp_oss_upload_{uuid.uuid4().hex[:8]}.jpg"
                cv2.imwrite(temp_file, frame)
                file_path = temp_file

            if custom_filename:
                oss_path = custom_filename
            else:
                base_path = self._get_oss_path(category)
                filename = os.path.basename(file_path)
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex[:8]
                oss_path = f"{base_path}/{timestamp}_{unique_id}_{filename}"

            result = self._bucket.put_object_from_file(oss_path, file_path)

            if result.status == 200:
                if OSS_DOMAIN:
                    file_url = f"{OSS_DOMAIN}/{oss_path}"
                else:
                    file_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{oss_path}"
                print(f"[INFO] 文件已上传到OSS: {file_url}")
                return file_url
            else:
                print(f"[ERROR] OSS上传失败，状态码: {result.status}")
                return None

        except Exception as e:
            print(f"[ERROR] OSS上传异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
    
    def upload_bytes(self, data, filename, category='img_predict'):
        """
        上传字节数据到OSS
        
        Args:
            data: 字节数据
            filename: 文件名
            category: 文件分类
        
        Returns:
            str: OSS文件URL，失败返回None
        """
        if not USE_OSS or not self._bucket:
            print("[WARN] OSS未启用或未初始化，无法上传文件")
            return None
        
        try:
            base_path = self._get_oss_path(category)
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex[:8]
            oss_filename = f"{timestamp}_{unique_id}_{filename}"
            oss_path = f"{base_path}/{oss_filename}"
            
            result = self._bucket.put_object(oss_path, data)
            
            if result.status == 200:
                if OSS_DOMAIN:
                    file_url = f"{OSS_DOMAIN}/{oss_path}"
                else:
                    file_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{oss_path}"
                
                print(f"[INFO] 字节数据已上传到OSS: {file_url}")
                return file_url
            else:
                print(f"[ERROR] OSS上传失败，状态码: {result.status}")
                return None
                
        except Exception as e:
            print(f"[ERROR] OSS上传异常: {str(e)}")
            return None
    
    def delete_file(self, oss_url):
        """
        从OSS删除文件
        
        Args:
            oss_url: OSS文件URL
        
        Returns:
            bool: 删除成功返回True，失败返回False
        """
        if not USE_OSS or not self._bucket:
            return False
        
        try:
            if OSS_DOMAIN and oss_url.startswith(OSS_DOMAIN):
                oss_path = oss_url.replace(f"{OSS_DOMAIN}/", "")
            elif OSS_BUCKET_NAME in oss_url:
                oss_path = oss_url.split(f"{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/")[-1]
            else:
                return False
            
            self._bucket.delete_object(oss_path)
            print(f"[INFO] 已从OSS删除文件: {oss_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] OSS删除文件失败: {str(e)}")
            return False
    
    def file_exists(self, oss_url):
        """
        检查OSS文件是否存在
        
        Args:
            oss_url: OSS文件URL
        
        Returns:
            bool: 存在返回True，不存在返回False
        """
        if not USE_OSS or not self._bucket:
            return False
        
        try:
            if OSS_DOMAIN and oss_url.startswith(OSS_DOMAIN):
                oss_path = oss_url.replace(f"{OSS_DOMAIN}/", "")
            elif OSS_BUCKET_NAME in oss_url:
                oss_path = oss_url.split(f"{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/")[-1]
            else:
                return False
            
            return self._bucket.object_exists(oss_path)
            
        except Exception as e:
            print(f"[ERROR] OSS检查文件失败: {str(e)}")
            return False


oss_uploader = OSSUploader()
