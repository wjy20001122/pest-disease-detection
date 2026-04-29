# -*- coding: utf-8 -*-
# @Time : 2024-12-26 12:10
# @File : mypredictor.py
# @Description : 图片检测预测器，支持YOLO和DETR模型

import json
import time
import os
import numpy as np
import cv2
import onnxruntime as ort
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

from app.ml import config
from app.ml.yolodetect import ImagePredictor as YOLOPredictor
from app.ml.detrdetect import ImagePredictor as DETRPredictor


def _load_chinese_font():
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
            return ImageFont.truetype(font_path, 24)
        except:
            continue
    return None


def _draw_text_pil(img: np.ndarray, text: str, position: Tuple[int, int],
                  font, color: Tuple[int, int, int]) -> np.ndarray:
    """使用PIL绘制中文"""
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x, y = position
    draw.rectangle([x, y - text_h - 5, x + text_w + 10, y], fill=color)
    draw.text((x + 5, y - text_h - 3), text, font=font, fill=(255, 255, 255))

    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


_chinese_font = _load_chinese_font()


def draw_detections_on_image(image: np.ndarray, results: Dict[str, Any],
                             english_labels: List[str] = None) -> np.ndarray:
    result_image = image.copy()

    boxes = results.get('boxes', [])
    confidences = results.get('confidences', [])
    class_ids = results.get('class_ids', [])

    for i, (box, conf, cid) in enumerate(zip(boxes, confidences, class_ids)):
        x1, y1, x2, y2 = box
        color = config.get_box_color(cid)

        if english_labels and cid < len(english_labels):
            label = english_labels[cid]
        else:
            label = f"class_{cid}"

        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)

        label_text = f"{label} {conf:.2f}"

        if _chinese_font:
            result_image = _draw_text_pil(result_image, label_text, (x1, y1 - 5), _chinese_font, color)
        else:
            (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                result_image,
                (x1, y1 - text_h - 10),
                (x1 + text_w, y1),
                color,
                -1
            )
            cv2.putText(
                result_image,
                label_text,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

    return result_image


class ONNXPredictor:
    def __init__(self, kind: str, img_path: str, save_path: str = "./runs/result.jpg", conf: float = 0.5):
        self.kind = kind
        self.img_path = img_path
        self.save_path = save_path
        self.conf = conf

        self.model_config = config.get_model_config(kind)
        self.model_arch = config.get_model_arch(kind)
        self.model_path = self.model_config.get('model_path', '')
        self.labels = config.get_classes(kind) or config.get_labels(kind)

        if self.model_arch == config.MODEL_ARCH_DETR:
            self.predictor = DETRPredictor(
                weights_path=self.model_path,
                img_path=img_path,
                kind=kind,
                save_path=save_path,
                conf=conf,
                use_nms=True,
                iou_threshold=self.model_config.get('iou_threshold', 0.5)
            )
        else:
            self.predictor = YOLOPredictor(
                weights_path=self.model_path,
                img_path=img_path,
                kind=kind,
                save_path=save_path,
                conf=conf
            )

    def predict(self, save_result: bool = True) -> Dict[str, Any]:
        results = self.predictor.predict(save_result=False)

        image = results.get('image')

        if results.get('labels') in ['预测失败', '无检测结果'] or image is None:
            if save_result and image is not None:
                os.makedirs(os.path.dirname(self.save_path) or '.', exist_ok=True)
                cv2.imwrite(self.save_path, image)
            return results

        result_image = draw_detections_on_image(image, results, self.labels)

        if save_result:
            os.makedirs(os.path.dirname(self.save_path) or '.', exist_ok=True)
            cv2.imwrite(self.save_path, result_image)

        return {
            'labels': results['labels'],
            'confidences': [f"{conf * 100:.2f}%" for conf in results['confidences']],
            'allTime': results['allTime'],
            'inferenceTime': results.get('inferenceTime', 0.0),
            'boxes': results['boxes'],
            'image': image
        }

    def draw_detections(self, image: np.ndarray, results: Dict[str, Any]) -> np.ndarray:
        return draw_detections_on_image(image, results, self.labels)