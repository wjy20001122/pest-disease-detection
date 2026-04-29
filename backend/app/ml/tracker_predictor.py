# -*- coding: utf-8 -*-
# @Time : 2026-03-28
# @Author : 魏继勇
# @File : tracker_predictor.py
# @Description : 实时跟踪预测器 - 支持OC-SORT + 贝叶斯匹配器

import numpy as np
import cv2
from typing import List, Tuple, Dict, Any
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

from app.ml import config
from app.ml import tracker_config
from app.ml.trackers.ocsort_tracker.ocsort import OCSort
from app.ml.trackers.ocsort_tracker.bayesian_matcher import BayesianMatcher


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> List[int]:
    """
    非极大值抑制（NMS）
    :param boxes: 边界框数组，形状为 (N, 4)，格式为 xyxy
    :param scores: 置信度数组，形状为 (N,)
    :param iou_threshold: IoU 阈值
    :return: 保留的索引列表
    """
    if len(boxes) == 0:
        return []
    
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
        
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        
        inds = np.where(ovr <= iou_threshold)[0]
        order = order[inds + 1]
    
    return keep


class TrackerPredictor:
    """实时跟踪预测器 - 结合检测器、OC-SORT跟踪器和贝叶斯匹配器"""

    def __init__(self, kind: str, conf: float = 0.5, tracker_type: str = 'ocsort', 
                 reset_id: bool = True, enable_bayesian: bool = True, **kwargs):
        """
        初始化TrackerPredictor
        :param kind: 作物类型（如'pest', 'pest_detr'等）
        :param conf: 置信度阈值
        :param tracker_type: 跟踪器类型（目前只支持'ocsort'）
        :param reset_id: 是否重置跟踪器ID计数器
        :param enable_bayesian: 是否启用贝叶斯匹配器
        :param kwargs: 其他参数
        """
        self.kind = kind
        self.conf = conf
        self.tracker_type = tracker_type.lower()
        self.enable_bayesian = enable_bayesian

        # 获取模型配置
        self.model_config = config.get_model_config(kind)
        self.model_arch = config.get_model_arch(kind)
        self.input_size = self.model_config.get('input_size', (640, 640))
        self.iou_threshold = self.model_config.get('iou_threshold', 0.5)
        
        # 获取类别信息
        self.classes = config.get_classes(kind)
        self.labels = self.classes
        self.english_labels = self.model_config.get('labels', self.classes)
        
        # 获取模型路径
        self.model_path = self.model_config.get('model_path', '')
        
        # 初始化检测器
        self._init_detector()

        # 创建OC-SORT跟踪器
        self.tracker = self._create_tracker()
        
        # 创建贝叶斯匹配器
        if self.enable_bayesian:
            bayesian_config = tracker_config.get_bayesian_config()
            self.bayesian_matcher = BayesianMatcher(bayesian_config)
        else:
            self.bayesian_matcher = None

        # 统计信息
        self.stats = {
            'total_counts': defaultdict(int),
            'current_frame': defaultdict(int),
            'total_tracks': 0,
            'unique_ids': set(),
            'bayesian_stats': {},
        }

        # 轨迹历史
        self.trajectory_history = defaultdict(list)
        self.max_trajectory_length = tracker_config.VISUALIZATION_CONFIG.get('trajectory_length', 30)
        
        # 帧计数器
        self.frame_counter = 0
        
        # 加载中文字体
        self.font = self._load_chinese_font()

    def _init_detector(self):
        """初始化检测器（ONNX Runtime）"""
        import onnxruntime as ort
        
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
        
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.output_names = [out.name for out in self.session.get_outputs()]
        
        self.is_detr = self.model_arch == config.MODEL_ARCH_DETR

    def _create_tracker(self) -> OCSort:
        """创建OC-SORT跟踪器"""
        cfg = tracker_config.get_tracker_config('ocsort')
        
        return OCSort(
            det_thresh=cfg['det_thresh'],
            max_age=cfg['max_age'],
            min_hits=cfg['min_hits'],
            iou_threshold=cfg['iou_threshold'],
            delta_t=cfg['delta_t'],
            asso_func=cfg['asso_func'],
            inertia=cfg['inertia'],
            use_byte=cfg['use_byte'],
            center_dist_threshold=cfg['center_dist_threshold'],
            adaptive_center_dist=cfg['adaptive_center_dist'],
            base_sigma_sq=cfg['base_sigma_sq'],
            center_dist_min=cfg['center_dist_min'],
            center_dist_max=cfg['center_dist_max'],
        )

    def _load_chinese_font(self):
        """加载中文字体"""
        import os as _os
        font_dir = _os.path.dirname(_os.path.abspath(__file__))
        local_font = _os.path.join(font_dir, 'fonts', 'wqy-microhei.ttc')

        font_paths = [
            local_font,
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/arphic/uming.ttc",
            "/usr/share/fonts/truetype/arphic/ukai.ttc",
        ]

        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, 20)
            except:
                continue
        return None

    def _preprocess_yolo(self, image: np.ndarray) -> np.ndarray:
        """YOLO模型预处理"""
        input_h, input_w = self.input_size
        resized = cv2.resize(image, (input_w, input_h))
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb_image.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(transposed, axis=0)

    def _preprocess_detr(self, image: np.ndarray) -> Tuple[np.ndarray, float, int, int]:
        """DETR模型预处理（letterbox）"""
        input_h, input_w = self.input_size
        orig_h, orig_w = image.shape[:2]
        
        scale = min(input_w / orig_w, input_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
        resized = cv2.resize(image, (new_w, new_h))
        
        padded = np.zeros((input_h, input_w, 3), dtype=np.uint8)
        pad_x = (input_w - new_w) // 2
        pad_y = (input_h - new_h) // 2
        padded[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        
        rgb_image = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        normalized = rgb_image.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        input_tensor = np.expand_dims(transposed, axis=0)
        
        return input_tensor, scale, pad_x, pad_y

    def _postprocess_yolo(self, outputs: np.ndarray, orig_shape: Tuple[int, int]) -> Dict[str, Any]:
        """YOLO模型后处理"""
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

    def _postprocess_detr(self, labels_output: np.ndarray, boxes_output: np.ndarray,
                         scores_output: np.ndarray, orig_shape: Tuple[int, int],
                         scale: float, pad_x: int, pad_y: int) -> Dict[str, Any]:
        """DETR模型后处理"""
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
            
            x1 = (x1 - pad_x) / scale
            y1 = (y1 - pad_y) / scale
            x2 = (x2 - pad_x) / scale
            y2 = (y2 - pad_y) / scale
            
            x1 = int(max(0, min(x1, orig_w)))
            y1 = int(max(0, min(y1, orig_h)))
            x2 = int(max(0, min(x2, orig_w)))
            y2 = int(max(0, min(y2, orig_h)))

            boxes.append([x1, y1, x2, y2])
            confidences.append(score)
            class_ids.append(class_id)

        if len(boxes) > 0:
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

    def _detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """执行检测"""
        orig_shape = frame.shape[:2]
        
        if self.is_detr:
            input_tensor, scale, pad_x, pad_y = self._preprocess_detr(frame)
            
            input_h, input_w = self.input_size
            input_feed = {
                'images': input_tensor,
                'orig_target_sizes': np.array([[input_h, input_w]], dtype=np.int64)
            }
            
            outputs = self.session.run(self.output_names, input_feed)
            
            output_dict = dict(zip(self.output_names, outputs))
            results = self._postprocess_detr(
                output_dict.get('labels'),
                output_dict.get('boxes'),
                output_dict.get('scores'),
                orig_shape,
                scale, pad_x, pad_y
            )
        else:
            input_tensor = self._preprocess_yolo(frame)
            outputs = self.session.run(self.output_names, {self.input_names[0]: input_tensor})
            results = self._postprocess_yolo(outputs[0], orig_shape)
        
        return results

    def track_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        跟踪单帧
        流程：
        1. OC-SORT先匹配
        2. 未匹配的检测框给贝叶斯匹配器
        3. 贝叶斯匹配成功 → 创建tracker并设置恢复的ID
        4. 贝叶斯匹配失败 → 创建新tracker（新ID）
        :param frame: 输入帧
        :return: 跟踪结果
        """
        self.frame_counter += 1
        
        # 执行检测
        det_results = self._detect(frame)
        
        # 准备检测框用于跟踪器
        boxes = det_results['boxes']
        confidences = det_results['confidences']
        class_ids = det_results['class_ids']
        labels = det_results['labels']
        
        # 构建检测结果数组 [x1, y1, x2, y2, score]
        if len(boxes) > 0:
            dets = np.array([[b[0], b[1], b[2], b[3], c] 
                           for b, c in zip(boxes, confidences)])
        else:
            dets = np.empty((0, 5))
        
        # OC-SORT 跟踪 - 返回未匹配的检测框索引
        orig_h, orig_w = frame.shape[:2]
        unmatched_dets, all_dets = self.tracker.update(dets, (orig_h, orig_w), (orig_h, orig_w))
        
        # 贝叶斯匹配器处理
        rematched_ids = []
        matched_det_indices = set()  # 记录已被匹配的检测框索引
        
        if self.enable_bayesian and self.bayesian_matcher and len(unmatched_dets) > 0:
            lost_trackers = self.tracker.get_lost_trackers()
            valid_track_ids = set(trk[0] for trk in lost_trackers)
            
            tracked_ids_set = set()
            for trk in self.tracker.trackers:
                if trk.time_since_update == 0:
                    tracked_ids_set.add(trk.id)
            
            for det_idx in unmatched_dets:
                det = all_dets[det_idx]
                box = [det[0], det[1], det[2], det[3]]
                conf = det[4]
                detection = {'box': box, 'conf': conf, 'class_id': 0, 'label': 'unknown'}
                recovered_id = self.bayesian_matcher.try_rematch(detection, tracked_ids_set, valid_track_ids)
                
                if recovered_id is not None:
                    if self.tracker.recover_tracker(recovered_id, det):
                        matched_det_indices.add(det_idx)
                        rematched_ids.append(recovered_id)
            
            new_detections = []
            for det_idx in unmatched_dets:
                det = all_dets[det_idx]
                cx = (det[0] + det[2]) / 2
                cy = (det[1] + det[3]) / 2
                w = det[2] - det[0]
                h = det[3] - det[1]
                new_detections.append((cx, cy, w, h))
            self.bayesian_matcher._adaptive_adjust_sigma(new_detections)
        
        # 先清理无用的tracker（释放ID供新tracker使用）
        self.tracker.cleanup_unused_trackers()
        
        # 对于仍然未匹配的检测框，创建新tracker
        for det_idx in unmatched_dets:
            if det_idx not in matched_det_indices:
                det = all_dets[det_idx]
                self.tracker.create_tracker(det)
        
        # 清理超过max_age的tracker
        self.tracker.cleanup_trackers()
        
        # 获取OC-SORT输出结果
        tracked = self.tracker.get_output()
        
        # 解析OC-SORT跟踪结果
        tracked_objects = []
        
        if len(tracked) > 0:
            for t in tracked:
                x1, y1, x2, y2, track_id = t
                track_id = int(track_id) - 1
                
                matched_idx = None
                for i, box in enumerate(boxes):
                    iou = self._compute_iou([x1, y1, x2, y2], box)
                    if iou > 0.5:
                        matched_idx = i
                        break
                
                if matched_idx is not None:
                    tracked_objects.append({
                        'box': [int(x1), int(y1), int(x2), int(y2)],
                        'track_id': track_id,
                        'conf': confidences[matched_idx],
                        'class_id': class_ids[matched_idx],
                        'label': labels[matched_idx]
                    })
                else:
                    tracked_objects.append({
                        'box': [int(x1), int(y1), int(x2), int(y2)],
                        'track_id': track_id,
                        'conf': 0.5,
                        'class_id': 0,
                        'label': self.labels[0] if self.labels else "unknown"
                    })
        
        # 更新贝叶斯匹配器的稳定轨迹库
        if self.enable_bayesian and self.bayesian_matcher:
            self.bayesian_matcher.update_stable_tracks(tracked_objects)
            
            self.stats['bayesian_stats'] = {
                'rematch_count': self.bayesian_matcher.rematch_count,
                'rematched_ids': rematched_ids,
                'stable_library_size': len(self.bayesian_matcher.stable_track_library),
                'sigma_sq': self.bayesian_matcher.sigma_sq,
            }
        
        # 提取结果
        tracked_boxes = [t['box'] for t in tracked_objects]
        tracked_ids = [t['track_id'] for t in tracked_objects]
        tracked_confidences = [t['conf'] for t in tracked_objects]
        tracked_class_ids = [t['class_id'] for t in tracked_objects]
        tracked_labels = [t['label'] for t in tracked_objects]
        
        # 更新轨迹历史
        for box, tid in zip(tracked_boxes, tracked_ids):
            center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            self.trajectory_history[tid].append(center)
            if len(self.trajectory_history[tid]) > self.max_trajectory_length:
                self.trajectory_history[tid].pop(0)
        
        # 更新统计
        self.stats['current_frame'].clear()
        for tid, label in zip(tracked_ids, tracked_labels):
            self.stats['current_frame'][label] += 1
            self.stats['total_counts'][label] += 1
            self.stats['unique_ids'].add(tid)
        
        self.stats['total_tracks'] = len(self.stats['unique_ids'])
        
        # 准备返回的 detections 列表用于数据采集
        detections = []
        for i in range(len(tracked_boxes)):
            detections.append({
                'track_id': tracked_ids[i],
                'class_name': tracked_labels[i],
                'bbox': tracked_boxes[i],
                'confidence': tracked_confidences[i]
            })
        
        return {
            'boxes': tracked_boxes,
            'tracker_ids': tracked_ids,
            'confidences': tracked_confidences,
            'class_ids': tracked_class_ids,
            'labels': tracked_labels,
            'detected': len(tracked_boxes) > 0,
            'interval': 1,
            'detections': detections,
            'stats': {
                'total_counts': dict(self.stats['total_counts']),
                'current_frame': dict(self.stats['current_frame']),
                'total_tracks': self.stats['total_tracks'],
                'bayesian_stats': self.stats.get('bayesian_stats', {}),
            }
        }

    def _compute_iou(self, box1: List[float], box2: List[float]) -> float:
        """计算两个框的IoU"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        
        return inter / union if union > 0 else 0

    def draw_detections(self, frame: np.ndarray, results: Dict[str, Any], 
                       show_stats: bool = True) -> np.ndarray:
        """
        绘制跟踪结果
        :param frame: 输入帧
        :param results: 跟踪结果
        :param show_stats: 是否显示统计信息
        :return: 绘制后的帧
        """
        result_frame = frame.copy()
        
        tracked_boxes = results.get('boxes', [])
        tracker_ids = results.get('tracker_ids', [])
        tracked_confidences = results.get('confidences', [])
        tracked_labels = results.get('labels', [])
        
        for i, (box, tid, conf, label) in enumerate(zip(tracked_boxes, tracker_ids, tracked_confidences, tracked_labels)):
            x1, y1, x2, y2 = box
            color = config.get_box_color(tid % 10)
            
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 2)
            
            text = f"{tid} {label} {conf:.2f}"
            
            if self.font:
                result_frame = self._draw_text_pil(result_frame, text, (x1, y1 - 5), color)
            else:
                cv2.putText(result_frame, text, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            if tid in self.trajectory_history and len(self.trajectory_history[tid]) > 1:
                trajectory = self.trajectory_history[tid]
                for j in range(1, len(trajectory)):
                    pt1 = (int(trajectory[j-1][0]), int(trajectory[j-1][1]))
                    pt2 = (int(trajectory[j][0]), int(trajectory[j][1]))
                    cv2.line(result_frame, pt1, pt2, color, 1)
        
        if show_stats:
            stats = results.get('stats', {})
            y_offset = 30
            cv2.putText(result_frame, f"Tracks: {stats.get('total_tracks', 0)}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            bayesian_stats = stats.get('bayesian_stats', {})
            if bayesian_stats and bayesian_stats.get('rematched_ids'):
                y_offset += 25
                rematched_str = ", ".join(map(str, bayesian_stats.get('rematched_ids', [])))
                cv2.putText(result_frame, f"Rematched: [{rematched_str}]", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        return result_frame

    def _draw_text_pil(self, img: np.ndarray, text: str, position: Tuple[int, int], 
                      color: Tuple[int, int, int]) -> np.ndarray:
        """使用PIL绘制中文"""
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        bbox = draw.textbbox((0, 0), text, font=self.font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x, y = position
        draw.rectangle([x, y - text_h - 5, x + text_w + 10, y], fill=color)
        draw.text((x + 5, y - text_h - 3), text, font=self.font, fill=(255, 255, 255))
        
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_counts': dict(self.stats['total_counts']),
            'current_frame': dict(self.stats['current_frame']),
            'total_tracks': self.stats['total_tracks'],
            'bayesian_stats': self.stats.get('bayesian_stats', {}),
        }
