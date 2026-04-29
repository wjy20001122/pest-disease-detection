# -*- coding: utf-8 -*-
# @Time : 2026-03-26
# @Author : 魏继勇
# @File : tracker_config.py
# @Description : 跟踪器配置文件 - 支持OC-SORT + 贝叶斯匹配器

import os

# ==========================================
# 跟踪器全局配置
# ==========================================

DEFAULT_TRACKER = 'ocsort'

TRACKER_TYPES = {
    'ocsort': 'OC-SORT 跟踪器',
}

# ==========================================
# OC-SORT 配置
# 参数说明: https://github.com/noahcao/OC-SORT
# ==========================================
OCSORT_CONFIG = {
    'det_thresh': 0.2,      # 检测阈值，低于此值的检测框不参与跟踪
    'max_age': 300,          # 最大丢失帧数，超过此值轨迹被删除（需大于max_lost_frames）
    'min_hits': 3,          # 最小命中次数，达到此值才输出轨迹
    'iou_threshold': 0.3,   # IoU关联阈值，用于匹配检测框和轨迹
    'delta_t': 2,           # 速度计算的时间间隔（帧数）
    'asso_func': 'iou',     # 关联函数: 'iou', 'giou', 'ciou', 'diou'
    'inertia': 0.2,         # 惯性权重，用于速度平滑
    'use_byte': False,      # 是否使用BYTE关联策略
    
    # 中心距离硬阈值配置
    'center_dist_threshold': 80.0,  # 基础中心距离阈值（像素）
    'adaptive_center_dist': True,   # 是否启用自适应中心距离阈值
    'base_sigma_sq': 150 * 150,     # 基准抖动方差，用于计算自适应阈值
    'center_dist_min': 40.0,        # 最小中心距离阈值
    'center_dist_max': 150.0,       # 最大中心距离阈值
}

# ==========================================
# 贝叶斯匹配器配置（轻量化，适合嵌入式设备）
#
# 核心思路：用"软概率"替代"硬阈值"
# - 风/震动的本质是：目标位置会"抖动"，但不会"瞬间瞬移"
# - 不用"距离<50像素就匹配"的硬规则，而是用概率计算
#
# 贝叶斯公式简化版：
#   Score_old = P(H0) × P(D|H0)  # 老虫子重现的得分
#   Score_new = P(H1) × P(D|H1)  # 新虫子的得分
#   如果 Score_old > Score_new → 判定为老虫子重现，恢复原ID
#   否则 → 不匹配，由OC-SORT分配新ID
BAYESIAN_MATCHER_CONFIG = {
    'enable': False,                      # 是否启用贝叶斯匹配器
    'sigma_sq': 150 * 150,              # 抖动方差，允许50像素的抖动范围
    'max_lost_frames': 250,              # 最大丢失帧数，超过此值从匹配库删除
    'min_stable_frames': 3,             # 最小稳定帧数，连续跟踪此帧数才入库
    
    # 先验概率 P(H0) - 基于丢失帧数
    # H0: 新目标是老虫子重现（不计数）
    # H1: 新目标是新虫子（计数+1）
    'prior_lost_1': 80,                 # 丢失1帧: P(H0)=0.80（大概率是遮挡/抖动）
    'prior_lost_2_3': 50,               # 丢失2-3帧: P(H0)=0.50
    'prior_lost_4_5': 10,               # 丢失4-5帧: P(H0)=0.20（大概率真走了）
    
    # 似然度 P(D|H0) - 基于距离平方
    # D: 新目标与老轨迹的距离
    'likelihood_very_near': 150,         # d² < σ²/4: 非常近，P(D|H0)=0.90
    'likelihood_near': 80,              # σ²/4 <= d² < σ²: 有点近，P(D|H0)=0.50
    'likelihood_far': 20,               # d² >= σ²: 比较远，P(D|H0)=0.10
    
    # 自适应抖动方差
    'adaptive_sigma': True,             # 是否启用自适应调整
    'sigma_increase_threshold': 4,      # 触发增大sigma的新目标数量阈值
    'sigma_max': 100 * 100,             # 最大抖动方差（风大时）
    'sigma_min': 30 * 30,               # 最小抖动方差（稳定时）
}

# ==========================================
# 检测器配置
# ==========================================

# ==========================================
# 可视化配置
# ==========================================
VISUALIZATION_CONFIG = {
    'trajectory_length': 300,            # 轨迹显示长度（帧数）
    'show_confidence': True,            # 是否显示置信度
    'show_label': True,                 # 是否显示标签
    'box_thickness': 2,                 # 检测框线宽
    'font_scale': 0.6,                  # 字体大小
}


def get_tracker_config(tracker_type: str) -> dict:
    """获取指定类型的跟踪器配置"""
    if tracker_type == 'ocsort':
        return OCSORT_CONFIG.copy()
    return OCSORT_CONFIG.copy()


def get_bayesian_config() -> dict:
    """获取贝叶斯匹配器配置"""
    return BAYESIAN_MATCHER_CONFIG.copy()
