# -*- coding: utf-8 -*-
# @Time : 2026-03-26
# @Author : 魏继勇
# @File : detrdetect.py
# @Description : DeIM DETR模型ONNX图片检测

import json
import time
import numpy as np
import cv2
import onnxruntime as ort
from typing import List, Tuple, Dict, Any, Optional
from app.ml import config


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> np.ndarray:
    """
    非极大值抑制 (NMS)
    :param boxes: 边界框数组，形状为 [N, 4]，格式为 [x1, y1, x2, y2]
    :param scores: 置信度数组，形状为 [N]
    :param iou_threshold: IoU阈值
    :return: 保留的框的索引
    """
    if len(boxes) == 0:
        return np.array([], dtype=np.int64)
    
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    
    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(i)
        
        if len(order) == 1:
            break
        
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        
        mask = iou < iou_threshold
        order = order[1:][mask]
    
    return np.array(keep, dtype=np.int64)


class ImagePredictor:
    """DeIM DETR模型ONNX图片检测器"""

    def __init__(self, weights_path: str, img_path: str, kind: str,
                 save_path: str = "./runs/result.jpg", conf: float = 0.5,
                 use_nms: bool = True, iou_threshold: float = 0.5):
        """
        初始化ImagePredictor类
        :param weights_path: 权重文件路径（ONNX模型路径）
        :param img_path: 输入图像路径
        :param kind: 作物类型（如'pest_detr'）
        :param save_path: 结果保存路径
        :param conf: 置信度阈值
        :param use_nms: 是否使用NMS（默认True）
        :param iou_threshold: NMS IoU阈值
        """
        self.img_path = img_path
        self.save_path = save_path
        self.conf = conf
        self.kind = kind
        self.use_nms = use_nms
        self.iou_threshold = iou_threshold

        self.model_config = config.get_model_config(kind)
        self.input_size = self.model_config.get('input_size', (640, 640))

        self.classes = config.get_classes(kind)
        self.labels = self.classes
        self.english_labels = self.model_config.get('labels', self.classes)

        self.model_path = weights_path if weights_path else self.model_config.get('model_path', '')

        self.session = None
        self.input_names = None
        self.output_names = None
        self._init_session()

    def _init_session(self):
        """初始化ONNX Runtime会话"""
        inference_config = config.get_inference_config()
        providers = inference_config.get('providers', ['CPUExecutionProvider'])
        cpu_opt = inference_config.get('cpu_optimization', {})

        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = cpu_opt.get('intra_op_num_threads', 4)
        sess_options.inter_op_num_threads = cpu_opt.get('inter_op_num_threads', 1)
        
        if cpu_opt.get('execution_mode', 'sequential') == 'sequential':
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        else:
            sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
        
        if cpu_opt.get('graph_optimization_level', 'all') == 'all':
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        elif cpu_opt.get('graph_optimization_level') == 'basic':
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC

        self.session = ort.InferenceSession(
            self.model_path,
            sess_options=sess_options,
            providers=providers
        )

        self.input_names = [input.name for input in self.session.get_inputs()]
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        print(f"[INFO] DeIM模型输入: {self.input_names}")
        print(f"[INFO] DeIM模型输出: {self.output_names}")

    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float, int, int]:
        """
        预处理图像（保持宽高比）
        :param image: 输入图像 (BGR格式)
        :return: (预处理后的图像张量 [1, 3, H, W], 缩放比例, 水平填充, 垂直填充)
        """
        input_h, input_w = self.input_size
        orig_h, orig_w = image.shape[:2]
        
        # 计算缩放比例（保持宽高比）
        scale = min(input_w / orig_w, input_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
        # 缩放图像
        resized = cv2.resize(image, (new_w, new_h))
        
        # 创建填充图像（黑色背景）
        padded = np.zeros((input_h, input_w, 3), dtype=np.uint8)
        pad_x = (input_w - new_w) // 2
        pad_y = (input_h - new_h) // 2
        padded[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        
        # 转换为 RGB 并归一化
        rgb_image = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        normalized = rgb_image.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        input_tensor = np.expand_dims(transposed, axis=0)
        
        return input_tensor, scale, pad_x, pad_y

    def postprocess(self, labels_output: np.ndarray, boxes_output: np.ndarray,
                    scores_output: np.ndarray, orig_shape: Tuple[int, int],
                    scale: float, pad_x: int, pad_y: int) -> Dict[str, Any]:
        """
        后处理DeIM输出
        :param labels_output: 标签输出 [1, num_detections] 或 [num_detections]
        :param boxes_output: 边界框输出 [1, num_detections, 4] 或 [num_detections, 4]，格式 [x1, y1, x2, y2]
        :param scores_output: 分数输出 [1, num_detections] 或 [num_detections]
        :param orig_shape: 原始图像尺寸 (height, width)
        :param scale: 缩放比例
        :param pad_x: 水平填充
        :param pad_y: 垂直填充
        :return: 检测结果字典
        """
        if len(labels_output.shape) == 2:
            labels_output = labels_output[0]
        if len(boxes_output.shape) == 3:
            boxes_output = boxes_output[0]
        if len(scores_output.shape) == 2:
            scores_output = scores_output[0]

        orig_h, orig_w = orig_shape

        boxes = []
        confidences = []
        class_ids = []

        num_detections = len(boxes_output) if boxes_output is not None else 0
        
        for i in range(num_detections):
            score = float(scores_output[i])
            
            if score < self.conf:
                continue
            
            class_id = int(labels_output[i])
            
            box = boxes_output[i]
            x1, y1, x2, y2 = box
            
            # DeIM 模型输出的是 640x640 图像上的坐标
            # 需要映射回原始图像坐标
            # 先减去 letterbox 填充，再除以缩放比例
            x1 = (x1 - pad_x) / scale
            y1 = (y1 - pad_y) / scale
            x2 = (x2 - pad_x) / scale
            y2 = (y2 - pad_y) / scale
            
            # 确保坐标在图像范围内
            x1 = int(max(0, min(x1, orig_w)))
            y1 = int(max(0, min(y1, orig_h)))
            x2 = int(max(0, min(x2, orig_w)))
            y2 = int(max(0, min(y2, orig_h)))

            boxes.append([x1, y1, x2, y2])
            confidences.append(score)
            class_ids.append(class_id)

        if len(boxes) > 0 and self.use_nms:
            boxes_array = np.array(boxes)
            scores_array = np.array(confidences)
            indices = nms(boxes_array, scores_array, self.iou_threshold)
            
            filtered_boxes = [boxes[i] for i in indices]
            filtered_confidences = [confidences[i] for i in indices]
            filtered_class_ids = [class_ids[i] for i in indices]
        else:
            filtered_boxes = boxes
            filtered_confidences = confidences
            filtered_class_ids = class_ids

        filtered_labels = []
        for cid in filtered_class_ids:
            if 0 <= cid < len(self.labels):
                filtered_labels.append(self.labels[cid])
            else:
                filtered_labels.append(f"class_{cid}")

        return {
            'boxes': filtered_boxes,
            'confidences': filtered_confidences,
            'class_ids': filtered_class_ids,
            'labels': filtered_labels,
            'num_detections': len(filtered_boxes)
        }

    def predict(self, save_result: bool = True) -> Dict[str, Any]:
        """
        预测图像
        :param save_result: 是否保存结果图片（由mypredictor处理）
        :return: 包含检测结果、原始图像和时间的字典
        """
        start_time = time.time()

        image = cv2.imread(self.img_path)
        if image is None:
            return {
                'labels': '预测失败',
                'confidences': "0.00%",
                'allTime': "0.000秒",
                'inferenceTime': 0.0,
                'image': None
            }

        orig_shape = image.shape[:2]
        orig_h, orig_w = orig_shape

        input_tensor, scale, pad_x, pad_y = self.preprocess(image)

        input_h, input_w = self.input_size
        
        input_feed = {}
        for name in self.input_names:
            if name == 'images':
                input_feed[name] = input_tensor
            elif name == 'orig_target_sizes':
                input_feed[name] = np.array([[input_h, input_w]], dtype=np.int64)
            else:
                input_feed[name] = np.array([])

        inference_start = time.time()
        outputs = self.session.run(self.output_names, input_feed)
        inference_end = time.time()
        inference_time = inference_end - inference_start

        output_dict = dict(zip(self.output_names, outputs))
        labels_output = output_dict.get('labels')
        boxes_output = output_dict.get('boxes')
        scores_output = output_dict.get('scores')
        
        print(f"[DEIM DEBUG] orig_target_sizes: [{orig_h}, {orig_w}]")
        print(f"[DEIM DEBUG] input_size: [{input_h}, {input_w}]")
        print(f"[DEIM DEBUG] scale: {scale}, pad_x: {pad_x}, pad_y: {pad_y}")
        if boxes_output is not None and len(boxes_output) > 0:
            print(f"[DEIM DEBUG] raw boxes (first 3): {boxes_output[0][:3] if len(boxes_output.shape) == 3 else boxes_output[:3]}")

        results = self.postprocess(labels_output, boxes_output, scores_output, orig_shape, scale, pad_x, pad_y)

        end_time = time.time()
        elapsed_time = end_time - start_time

        if results['num_detections'] == 0:
            return {
                'labels': '无检测结果',
                'confidences': [],
                'allTime': f"{elapsed_time:.3f}秒",
                'inferenceTime': inference_time,
                'image': image,
                'boxes': [],
                'class_ids': []
            }

        return {
            'labels': results['labels'],
            'confidences': results['confidences'],
            'allTime': f"{elapsed_time:.3f}秒",
            'inferenceTime': inference_time,
            'boxes': results['boxes'],
            'class_ids': results['class_ids'],
            'image': image
        }


if __name__ == '__main__':
    import os
    os.makedirs('./runs', exist_ok=True)

    predictor = ImagePredictor(
        weights_path='./weights/deim.onnx',
        img_path='19.jpg',
        kind='pest_detr',
        save_path='./runs/result_detr.jpg',
        conf=0.5,
        use_nms=True,
        iou_threshold=0.5
    )

    result = predictor.predict()
    print(f"结果: {result['labels']}")
    print(f"置信度: {result['confidences']}")
    print(f"时间: {result['allTime']}")
