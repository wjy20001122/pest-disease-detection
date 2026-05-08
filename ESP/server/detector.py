from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from .config import BOX_COLORS, CLASSES, ENGLISH_LABELS, settings


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> np.ndarray:
    if boxes.size == 0:
        return np.array([], dtype=np.int64)

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep = []

    while order.size > 0:
        current = order[0]
        keep.append(current)

        xx1 = np.maximum(x1[current], x1[order[1:]])
        yy1 = np.maximum(y1[current], y1[order[1:]])
        xx2 = np.minimum(x2[current], x2[order[1:]])
        yy2 = np.minimum(y2[current], y2[order[1:]])
        width = np.maximum(0.0, xx2 - xx1 + 1)
        height = np.maximum(0.0, yy2 - yy1 + 1)
        inter = width * height
        iou = inter / (areas[current] + areas[order[1:]] - inter)
        order = order[np.where(iou <= iou_threshold)[0] + 1]

    return np.array(keep, dtype=np.int64)


class EdgeDetectionEngine:
    def __init__(self, model_path: Path | str = settings.model_path) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 4
        sess_options.inter_op_num_threads = 1
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.input_size = (settings.input_height, settings.input_width)

    def detect(self, frame: np.ndarray, conf: float | None = None) -> dict[str, Any]:
        started = time.time()
        threshold = settings.conf_threshold if conf is None else conf
        input_tensor = self._preprocess(frame)
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})[0]
        detections = self._postprocess(outputs, frame.shape[:2], threshold)
        annotated = self.draw(frame, detections)
        return {
            "detections": detections,
            "annotated": annotated,
            "inference_ms": round((time.time() - started) * 1000, 2),
        }

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        input_h, input_w = self.input_size
        resized = cv2.resize(frame, (input_w, input_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(transposed, axis=0)

    def _postprocess(self, outputs: np.ndarray, orig_shape: tuple[int, int], conf: float) -> list[dict[str, Any]]:
        predictions = outputs[0].T
        orig_h, orig_w = orig_shape
        input_h, input_w = self.input_size
        scale_x = orig_w / input_w
        scale_y = orig_h / input_h
        boxes: list[list[int]] = []
        scores: list[float] = []
        class_ids: list[int] = []

        for pred in predictions:
            x_center, y_center, width, height = pred[0:4]
            class_scores = pred[4:]
            class_id = int(np.argmax(class_scores))
            score = float(class_scores[class_id])
            if score < conf:
                continue

            x_center *= scale_x
            y_center *= scale_y
            width *= scale_x
            height *= scale_y
            x1 = max(0, int(x_center - width / 2))
            y1 = max(0, int(y_center - height / 2))
            x2 = min(orig_w, int(x_center + width / 2))
            y2 = min(orig_h, int(y_center + height / 2))
            boxes.append([x1, y1, x2, y2])
            scores.append(score)
            class_ids.append(class_id)

        if not boxes:
            return []

        keep = nms(np.array(boxes), np.array(scores), settings.iou_threshold)
        detections = []
        for index in keep:
            class_id = class_ids[int(index)]
            label = CLASSES[class_id] if class_id < len(CLASSES) else f"class_{class_id}"
            english_label = ENGLISH_LABELS[class_id] if class_id < len(ENGLISH_LABELS) else label
            detections.append(
                {
                    "class_id": class_id,
                    "label": label,
                    "english_label": english_label,
                    "confidence": round(scores[int(index)], 4),
                    "bbox": boxes[int(index)],
                }
            )
        return detections

    def draw(self, frame: np.ndarray, detections: list[dict[str, Any]]) -> np.ndarray:
        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            class_id = int(det["class_id"])
            color = BOX_COLORS[class_id % len(BOX_COLORS)]
            label = f"{det['english_label']} {det['confidence']:.2f}"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            text_w, text_h = text_size
            y_text = max(text_h + 8, y1)
            cv2.rectangle(annotated, (x1, y_text - text_h - 8), (x1 + text_w + 8, y_text), color, -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 4, y_text - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return annotated
