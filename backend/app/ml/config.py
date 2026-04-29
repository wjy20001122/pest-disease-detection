# -*- coding: utf-8 -*-
# @Time : 2024-12-26
# @File : config.py
# @Description : 模型配置文件

import os
from pathlib import Path

FASTAPI_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = FASTAPI_ROOT.parent

MODEL_ARCH_YOLO = "yolo"
MODEL_ARCH_DETR = "detr"

MODELS_CONFIG = {
    "pest": {
        "name": "害虫检测",
        "type": "yolo",
        "model_path": str(FASTAPI_ROOT / "app/ml/weights/yolo12.onnx"),
        "input_size": (640, 640),
        "iou_threshold": 0.5,
        "conf_threshold": 0.35,
        "labels": ["aphid", "Corn_fall_armyworm_larva", "Corn_yellow_stem_borer_larva", "Corn_yellow_stem_borer"],
        "classes": ["蚜虫", "玉米粘虫幼虫", "玉米螟幼虫", "玉米螟成虫"],
        "description": "玉米害虫检测模型，支持四种主要害虫识别"
    },
    "pest_detr": {
        "name": "害虫检测 (DEIM)",
        "type": "detr",
        "model_path": str(FASTAPI_ROOT / "app/ml/weights/deim2p3.onnx"),
        "input_size": (640, 640),
        "iou_threshold": 0.7,
        "conf_threshold": 0.2,
        "labels": ["aphid", "Corn_fall_armyworm_larva", "Corn_yellow_stem_borer_larva", "Corn_yellow_stem_borer"],
        "classes": ["蚜虫", "玉米粘虫幼虫", "玉米螟幼虫", "玉米螟成虫"],
        "description": "玉米害虫检测模型(DEIM架构)，支持四种主要害虫识别"
    }
}

DISEASES_INFO = {
    "蚜虫": {
        "name": "蚜虫",
        "category": "虫害",
        "symptoms": "叶片卷曲、发黄，茎秆变形，植株生长受阻。大量发生时可见蜜露分泌。",
        "conditions": "温暖干燥环境适宜繁殖，适宜温度20-28℃。春秋季高发。",
        "prevention": "农业防治：清除田间杂草，合理密植。化学防治：可用吡虫啉、啶虫脒等药剂喷雾。生物防治：释放瓢虫、草蛉等天敌。"
    },
    "玉米粘虫幼虫": {
        "name": "玉米粘虫幼虫",
        "category": "虫害",
        "symptoms": "叶片被啃食成缺刻，严重时吃光叶片，仅剩叶脉。幼虫白天潜伏，夜间取食。",
        "conditions": "喜温暖潮湿，适宜温度22-28℃。暴食性害虫，发生量大时可在短期内将叶片吃光。",
        "prevention": "农业防治：深耕灭蛹，清除杂草。物理防治：点灯诱杀成虫。化学防治：可用氯虫苯甲酰胺、甲维盐等药剂喷雾。"
    },
    "玉米螟幼虫": {
        "name": "玉米螟幼虫",
        "category": "虫害",
        "symptoms": "叶片出现排孔，茎秆被蛀食，造成风折。心叶期受害最重，影响玉米生长。",
        "conditions": "温度24-28℃，相对湿度60%以上适宜发生。主要危害玉米心叶期和穗期。",
        "prevention": "农业防治：选用抗虫品种，处理秸秆消灭越冬幼虫。生物防治：释放赤眼蜂。化学防治：心叶期可用辛硫磷颗粒剂灌心。"
    },
    "玉米螟成虫": {
        "name": "玉米螟成虫",
        "category": "虫害",
        "symptoms": "成虫本身不直接危害，但会产卵繁殖后代。卵块多产于叶片背面，孵化后幼虫钻入茎秆危害。",
        "conditions": "夜间活动，有强趋光性。高温高湿条件下繁殖快。",
        "prevention": "物理防治：点灯诱杀成虫。农业防治：秸秆还田时粉碎杀死越冬幼虫。生物防治：释放赤眼蜂控制卵块。"
    }
}

INFERENCE_CONFIG = {
    "providers": ["CPUExecutionProvider"],
    "cpu_optimization": {
        "intra_op_num_threads": 4,
        "inter_op_num_threads": 1,
        "execution_mode": "sequential",
        "graph_optimization_level": "all"
    }
}

BOX_COLORS = [
    (255, 0, 0),    # 红色
    (0, 255, 0),    # 绿色
    (0, 0, 255),    # 蓝色
    (255, 255, 0),  # 黄色
    (255, 0, 255),  # 紫色
    (0, 255, 255),  # 青色
    (255, 128, 0),  # 橙色
    (128, 0, 255),  # 紫罗兰
    (0, 128, 255),  # 天蓝
    (255, 0, 128),  # 玫红
]


def get_model_config(kind: str):
    """获取模型配置"""
    return MODELS_CONFIG.get(kind)


def get_model_arch(kind: str):
    """获取模型架构类型"""
    config = get_model_config(kind)
    if not config:
        return MODEL_ARCH_YOLO
    return MODEL_ARCH_DETR if config.get("type") == "detr" else MODEL_ARCH_YOLO


def get_model_name_by_kind(kind: str) -> str:
    """根据kind获取模型名称"""
    config = get_model_config(kind)
    return config.get("name", kind) if config else kind


def get_kind_by_model_name(model_name: str) -> str:
    """根据模型名称获取kind"""
    for kind, config in MODELS_CONFIG.items():
        if config.get("name") == model_name:
            return kind
    return model_name


def get_classes(kind: str):
    """获取模型类别列表"""
    config = get_model_config(kind)
    return config.get("classes", []) if config else []


def get_labels(kind: str):
    """获取模型标签列表"""
    config = get_model_config(kind)
    return config.get("labels", []) if config else []


def get_input_size(kind: str) -> tuple:
    """获取模型输入尺寸"""
    config = get_model_config(kind)
    return config.get("input_size", (640, 640)) if config else (640, 640)


def get_inference_config() -> dict:
    """获取推理配置"""
    return INFERENCE_CONFIG


def get_box_color(class_id: int) -> tuple:
    """获取检测框颜色"""
    return BOX_COLORS[class_id % len(BOX_COLORS)]


def get_all_model_keys() -> list:
    """获取所有模型key"""
    return list(MODELS_CONFIG.keys())


def get_config_by_model_name(model_name: str) -> dict:
    """根据模型名称获取配置"""
    for config in MODELS_CONFIG.values():
        if config.get("name") == model_name:
            return config
    return None
