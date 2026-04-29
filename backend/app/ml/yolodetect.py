# -*- coding: utf-8 -*-
# @Time : 2026-03-26
# @Author : 魏继勇
# @File : yolodetect.py
# @Description : YOLO模型ONNX图片检测

import json
import time
import numpy as np
import cv2
import onnxruntime as ort
from typing import List, Tuple, Dict, Any, Optional
from app.ml import config


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> np.ndarray:
    """
    非极大值抑制 (NMS)
    :param boxes: 边界框数组，形状为 [N, 4]，格式为 [x1, y1, x2, y2]
    :param scores: 置信度数组，形状为 [N]
    :param iou_threshold: IoU 阈值
    :return: 保留的框的索引
    """
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h

        iou = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return np.array(keep)


class ImagePredictor:
    """YOLO模型ONNX图片检测器"""

    def __init__(self, weights_path: str, img_path: str, kind: str,
                 save_path: str = "./runs/result.jpg", conf: float = 0.5):
        """
        初始化ImagePredictor类
        :param weights_path: 权重文件路径（ONNX模型路径）
        :param img_path: 输入图像路径
        :param kind: 作物类型（如'pest', 'rice', 'corn'等）
        :param save_path: 结果保存路径
        :param conf: 置信度阈值
        """
        self.img_path = img_path
        self.save_path = save_path
        self.conf = conf
        self.kind = kind

        self.model_config = config.get_model_config(kind)
        self.input_size = self.model_config.get('input_size', (640, 640))
        self.iou_threshold = self.model_config.get('iou_threshold', 0.5)

        self.classes = config.get_classes(kind)
        self.labels = self.classes
        self.english_labels = self.model_config.get('labels', self.classes)

        self.model_path = weights_path if weights_path else self.model_config.get('model_path', '')

        self.session = None
        self.input_name = None
        self.output_name = None
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

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        预处理图像
        :param image: 输入图像 (BGR格式)
        :return: 预处理后的图像张量
        """
        input_h, input_w = self.input_size
        resized = cv2.resize(image, (input_w, input_h))
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb_image.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        input_tensor = np.expand_dims(transposed, axis=0)
        return input_tensor

    def postprocess(self, outputs: np.ndarray, orig_shape: Tuple[int, int]) -> Dict[str, Any]:
        """
        后处理YOLO输出
        :param outputs: 模型输出，格式 [batch, 4 + num_classes, num_anchors]
        :param orig_shape: 原始图像尺寸 (height, width)
        :return: 检测结果字典
        """
        predictions = outputs[0].T

        boxes = []
        confidences = []
        class_ids = []

        orig_h, orig_w = orig_shape
        input_h, input_w = self.input_size
        scale_x = orig_w / input_w
        scale_y = orig_h / input_h

        for pred in predictions:
            x_center, y_center, width, height = pred[0:4]
            class_scores = pred[4:]
            class_id = np.argmax(class_scores)
            class_confidence = class_scores[class_id]

            if class_confidence < self.conf:
                continue

            x_center *= scale_x
            y_center *= scale_y
            width *= scale_x
            height *= scale_y

            x1 = int(x_center - width / 2)
            y1 = int(y_center - height / 2)
            x2 = int(x_center + width / 2)
            y2 = int(y_center + height / 2)

            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(orig_w, x2)
            y2 = min(orig_h, y2)

            boxes.append([x1, y1, x2, y2])
            confidences.append(float(class_confidence))
            class_ids.append(int(class_id))

        if len(boxes) > 0:
            boxes_array = np.array(boxes)
            scores_array = np.array(confidences)
            indices = nms(boxes_array, scores_array, self.iou_threshold)

            filtered_boxes = [boxes[i] for i in indices]
            filtered_confidences = [confidences[i] for i in indices]
            filtered_class_ids = [class_ids[i] for i in indices]
        else:
            filtered_boxes = []
            filtered_confidences = []
            filtered_class_ids = []

        filtered_labels = []
        for cid in filtered_class_ids:
            if cid < len(self.labels):
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

        input_tensor = self.preprocess(image)

        inference_start = time.time()
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})[0]
        inference_end = time.time()
        inference_time = inference_end - inference_start

        results = self.postprocess(outputs, orig_shape)

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
            'confidences': [conf for conf in results['confidences']],
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
        weights_path='./weights/pest_detect.onnx',
        img_path='19.jpg',
        kind='pest',
        save_path='./runs/result.jpg',
        conf=0.4
    )

    result = predictor.predict()
    print(f"结果: {result['labels']}")
    print(f"置信度: {result['confidences']}")
    print(f"时间: {result['allTime']}")
