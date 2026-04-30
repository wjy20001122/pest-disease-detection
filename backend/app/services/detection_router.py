import httpx
import asyncio
import json
from typing import Optional, Dict, Any, List
from enum import Enum


class DetectionSource(str, Enum):
    LOCAL_MODEL = "local_model"
    CLOUD_AI = "cloud_ai"
    HYBRID = "hybrid"
    NO_PEST = "no_pest"
    CONFIRMED_NO_PEST = "confirmed_no_pest"


class DetectionRouter:
    """
    智能检测路由服务
    1. AI分析图像，选择最可能的病虫害类型和模型
    2. 调用本地模型检测
    3. 如果检测无病害，用知识库+AI二次确认真的无病虫害
    """

    LOCAL_MODEL_KEYWORDS = {
        "蚜虫": ["蚜虫", "aphid"],
        "玉米粘虫幼虫": ["玉米粘虫幼虫", "粘虫", "Corn_fall_armyworm_larva"],
        "玉米螟幼虫": ["玉米螟幼虫", "玉米螟", "Corn_yellow_stem_borer_larva"],
        "玉米螟成虫": ["玉米螟成虫", "Corn_yellow_stem_borer"],
    }

    KNOWLEDGE_PEST_TO_MODEL = {
        "蚜虫": "pest",
        "玉米粘虫幼虫": "pest",
        "玉米螟幼虫": "pest",
        "玉米螟成虫": "pest",
    }

    def __init__(self):
        self.deepseek_service = None

    def _init_deepseek(self):
        if self.deepseek_service is None:
            from app.services.deepseek_service import deepseek_service
            self.deepseek_service = deepseek_service

    async def route_detection(
        self,
        image_url: str,
        preferred_model_key: Optional[str] = None,
        use_local_model: bool = True,
        force_cloud_only: bool = False,
        allow_cloud_fallback: bool = True,
        include_ai_advice: bool = False,
        fallback_notice: str = "本地模型未识别到有效结果，已回退云端分析，结论未必完全可信。",
    ) -> Dict[str, Any]:
        """
        执行智能检测路由
        """
        local_result = None
        selected_model = preferred_model_key or "pest"

        if not force_cloud_only and use_local_model:
            local_result = await self._local_model_detect(image_url, selected_model)
            local_result = self._normalize_local_result(local_result)
            has_local_detection = (
                local_result
                and not local_result.get("error")
                and local_result.get("labels")
            )
            if has_local_detection:
                ai_result = {}
                if include_ai_advice:
                    ai_result = await self._analyze_local_detection_with_ai(image_url, local_result)
                merged_result = self._merge_results(
                    ai_result or {
                        "crop_type": "",
                        "diseases": [],
                        "analysis_notes": "本次结果基于用户选择的本地模型",
                    },
                    local_result,
                    None,
                )
                return {
                    "source": DetectionSource.LOCAL_MODEL,
                    "ai_analysis": ai_result,
                    "has_pest": True,
                    "knowledge_match": None,
                    "local_detection": local_result,
                    "matched_models": [selected_model],
                    "confirmed_no_pest": False,
                    "merged_result": merged_result,
                    "maybe_unreliable": False,
                    "confidence_notice": "local_model_selected",
                }

        if not allow_cloud_fallback:
            return {
                "source": DetectionSource.NO_PEST,
                "ai_analysis": {},
                "has_pest": False,
                "knowledge_match": None,
                "local_detection": local_result,
                "matched_models": [selected_model],
                "confirmed_no_pest": False,
                "maybe_unreliable": False,
                "confidence_notice": "local_model_only",
                "message": "本地模型未识别到有效结果，且当前已禁用云端回退。",
            }

        ai_result = await self._cloud_ai_analyze(image_url)

        if not ai_result or ai_result.get("error"):
            return {
                "source": DetectionSource.CLOUD_AI,
                "ai_analysis": ai_result,
                "has_pest": None,
                "knowledge_match": None,
                "local_detection": local_result,
                "matched_models": [selected_model],
                "confirmed_no_pest": False,
                "maybe_unreliable": True,
                "confidence_notice": "cloud_fallback_limited_confidence",
                "message": fallback_notice,
            }

        has_pest_ai = ai_result.get("has_pest", False)

        if force_cloud_only or not use_local_model:
            return {
                "source": DetectionSource.CLOUD_AI,
                "ai_analysis": ai_result,
                "has_pest": has_pest_ai,
                "knowledge_match": None,
                "local_detection": None,
                "matched_models": [selected_model],
                "confirmed_no_pest": False,
                "maybe_unreliable": True,
                "confidence_notice": "cloud_only_limited_confidence",
                "message": fallback_notice,
            }

        has_local_detection = local_result and not local_result.get("error") and local_result.get("labels")

        knowledge_match = None
        confirmed_no_pest = False

        if not has_local_detection:
            knowledge_match = await self._search_knowledge_by_ai_result(ai_result)

            if not knowledge_match:
                confirmed = await self._confirm_no_pest_with_ai(image_url, ai_result)
                if confirmed:
                    confirmed_no_pest = True
                    return {
                        "source": DetectionSource.CONFIRMED_NO_PEST,
                        "ai_analysis": ai_result,
                        "has_pest": False,
                        "knowledge_match": None,
                        "local_detection": local_result,
                        "matched_models": [selected_model],
                        "confirmed_no_pest": True,
                        "message": "经AI与知识库综合分析，确认图像中无病虫害",
                        "maybe_unreliable": True,
                        "confidence_notice": "cloud_fallback_limited_confidence",
                    }

        merged_result = self._merge_results(ai_result, local_result, knowledge_match)

        return {
            "source": DetectionSource.LOCAL_MODEL if has_local_detection else DetectionSource.CLOUD_AI,
            "ai_analysis": ai_result,
            "has_pest": has_local_detection or has_pest_ai,
            "knowledge_match": knowledge_match,
            "local_detection": local_result,
            "matched_models": [selected_model],
            "confirmed_no_pest": confirmed_no_pest,
            "merged_result": merged_result,
            "maybe_unreliable": not has_local_detection,
            "confidence_notice": "cloud_fallback_limited_confidence" if not has_local_detection else "local_model_selected",
            "message": fallback_notice if not has_local_detection else "本地模型已完成检测。",
        }

    async def _cloud_ai_analyze(self, image_url: str) -> Dict[str, Any]:
        """调用云端AI进行初步分析"""
        self._init_deepseek()

        if not self.deepseek_service.api_key:
            return {
                "error": "DeepSeek API未配置",
                "has_pest": None,
                "no_pest_confidence": 0,
                "diseases": [],
                "model_match_keywords": []
            }

        try:
            result = await self.deepseek_service.analyze_image_url(image_url)
            return result
        except Exception as e:
            return {
                "error": str(e),
                "has_pest": None,
                "no_pest_confidence": 0,
                "diseases": [],
                "model_match_keywords": []
            }

    async def _confirm_no_pest_with_ai(self, image_url: str, ai_result: Dict[str, Any]) -> bool:
        """用AI二次确认是否真的无病虫害"""
        self._init_deepseek()

        if not self.deepseek_service.api_key:
            return False

        try:
            confirmed = await self.deepseek_service.confirm_no_pest(image_url, ai_result)
            return confirmed
        except Exception:
            return False

    async def _search_knowledge_by_ai_result(self, ai_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """根据AI分析结果检索知识库"""
        try:
            from app.api.routers.knowledge import search_knowledge

            keywords = ai_result.get("model_match_keywords", [])
            diseases = ai_result.get("diseases", [])

            for disease in diseases:
                disease_name = disease.get("name", "")
                if disease_name:
                    results = search_knowledge(keyword=disease_name)
                    if results:
                        return results[0]

            for keyword in keywords:
                results = search_knowledge(keyword=keyword)
                if results:
                    return results[0]

            return None
        except Exception:
            return None

    def _match_pests_from_ai(self, ai_result: Dict[str, Any]) -> List[str]:
        """从AI分析结果中匹配本地支持的病虫害"""
        matched = []

        if ai_result.get("error"):
            return matched

        model_match_keywords = ai_result.get("model_match_keywords", [])

        for disease_name, keywords in self.LOCAL_MODEL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in model_match_keywords:
                    matched.append(disease_name)
                    break
                for ai_keyword in model_match_keywords:
                    if keyword in ai_keyword or ai_keyword in keyword:
                        matched.append(disease_name)
                        break

        diseases = ai_result.get("diseases", [])
        for disease in diseases:
            disease_name = disease.get("name", "")
            for name, keywords in self.LOCAL_MODEL_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in disease_name:
                        matched.append(name)
                        break

        return list(set(matched))

    def _select_best_model(self, matched_pests: List[str]) -> str:
        """根据匹配的病虫害选择最佳模型"""
        if not matched_pests:
            return "pest"

        for pest in matched_pests:
            if pest in self.KNOWLEDGE_PEST_TO_MODEL:
                return self.KNOWLEDGE_PEST_TO_MODEL[pest]

        return "pest"

    async def _local_model_detect(
        self,
        image_url: str,
        model_key: str
    ) -> Optional[Dict[str, Any]]:
        """调用本地模型进行检测"""
        from app.services.prediction_service import prediction_service

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: prediction_service.predict_image({
                "inputImg": image_url,
                "modelKey": model_key
            }))
            return result
        except Exception as e:
            return {"error": str(e), "detections": [], "labels": []}

    def _normalize_local_result(self, local_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not local_result or local_result.get("error"):
            return local_result

        normalized = dict(local_result)

        labels = normalized.get("labels")
        if not isinstance(labels, list):
            raw_labels = normalized.get("label", [])
            if isinstance(raw_labels, str):
                try:
                    raw_labels = json.loads(raw_labels)
                except Exception:
                    raw_labels = []
            labels = raw_labels if isinstance(raw_labels, list) else []
        normalized["labels"] = labels

        confidences = normalized.get("confidences")
        if not isinstance(confidences, list):
            raw_confidences = normalized.get("confidence", [])
            if isinstance(raw_confidences, str):
                try:
                    raw_confidences = json.loads(raw_confidences)
                except Exception:
                    raw_confidences = []
            confidences = raw_confidences if isinstance(raw_confidences, list) else []
        normalized["confidences"] = confidences

        detections = normalized.get("detections")
        if not isinstance(detections, list):
            detections = []
            boxes = normalized.get("boxes", [])
            for idx, label in enumerate(labels):
                conf_raw = confidences[idx] if idx < len(confidences) else 0
                conf_value = self._parse_confidence(conf_raw)
                bbox = boxes[idx] if idx < len(boxes) else None
                detections.append(
                    {
                        "class": label,
                        "class_name": label,
                        "confidence": conf_value,
                        "bbox": bbox,
                    }
                )
        normalized["detections"] = detections
        return normalized

    def _parse_confidence(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            number = float(value)
            return number if number <= 1 else number / 100.0
        if isinstance(value, str):
            cleaned = value.strip().replace("%", "")
            try:
                number = float(cleaned)
                return number if number <= 1 else number / 100.0
            except Exception:
                return 0.0
        return 0.0

    def _local_context_for_ai(self, local_result: Dict[str, Any]) -> Dict[str, Any]:
        labels = local_result.get("labels", [])
        detections = local_result.get("detections", [])
        label_counts: Dict[str, int] = {}
        max_confidence: Dict[str, float] = {}
        for idx, label in enumerate(labels):
            label_counts[label] = label_counts.get(label, 0) + 1
            conf_raw = local_result.get("confidences", [])[idx] if idx < len(local_result.get("confidences", [])) else 0
            conf_value = self._parse_confidence(conf_raw)
            max_confidence[label] = max(max_confidence.get(label, 0.0), conf_value)

        summary_items = [
            {
                "name": name,
                "count": count,
                "max_confidence": round(max_confidence.get(name, 0.0), 4),
            }
            for name, count in label_counts.items()
        ]

        return {
            "summary": summary_items,
            "labels": labels,
            "detections": detections[:30],
            "detection_count": len(labels),
        }

    async def _analyze_local_detection_with_ai(self, image_url: str, local_result: Dict[str, Any]) -> Dict[str, Any]:
        context = self._local_context_for_ai(local_result)
        self._init_deepseek()

        if not self.deepseek_service.api_key:
            diseases = []
            for item in context["summary"]:
                conf = float(item.get("max_confidence") or 0.0)
                diseases.append(
                    {
                        "name": item.get("name", "未知目标"),
                        "confidence": conf,
                        "severity": "high" if conf >= 0.8 else ("medium" if conf >= 0.5 else "low"),
                        "symptoms": "本地模型检测到该病虫害目标，请结合检测框位置实地复核。",
                        "possible_causes": "田间环境、虫源扩散或作物长势压力可能导致发生。",
                        "prevention": "建议优先进行田间复核，随后按知识库和农技规范采取防治措施。",
                    }
                )
            return {
                "crop_type": "",
                "has_pest": len(diseases) > 0,
                "no_pest_confidence": 0.0,
                "diseases": diseases,
                "model_match_keywords": context.get("labels", []),
                "analysis_notes": "未配置DeepSeek，当前建议基于本地检测结果自动生成。",
            }

        try:
            result = await self.deepseek_service.analyze_with_detection_context(image_url, context)
            if isinstance(result, dict):
                result.setdefault("analysis_notes", "AI建议基于本地检测结构结果生成。")
                result.setdefault("model_match_keywords", context.get("labels", []))
                return result
        except Exception:
            pass

        return {
            "crop_type": "",
            "has_pest": True,
            "no_pest_confidence": 0.0,
            "diseases": [],
            "model_match_keywords": context.get("labels", []),
            "analysis_notes": "AI建议生成失败，已回退为本地检测结果。",
        }

    def _merge_results(
        self,
        ai_result: Dict[str, Any],
        local_result: Optional[Dict[str, Any]],
        knowledge_match: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """合并云端AI、本地模型和知识库的结果"""
        has_local_detection = local_result and not local_result.get("error") and local_result.get("labels")

        local_detections = []
        local_labels = []
        if has_local_detection:
            local_detections = local_result.get("detections", [])
            local_labels = local_result.get("labels", [])

        merged_diseases = []

        if has_local_detection and local_labels:
            detected_pests_set = set()
            for label in local_labels:
                for name, keywords in self.LOCAL_MODEL_KEYWORDS.items():
                    if any(k in label for k in keywords):
                        detected_pests_set.add(name)

            for pest_name in detected_pests_set:
                confidence = 0.9
                for det in local_detections:
                    if any(k in det.get("class", "") for k in self.LOCAL_MODEL_KEYWORDS.get(pest_name, [])):
                        confidence = max(confidence, det.get("confidence", 0.9))

                disease_info = {
                    "name": pest_name,
                    "confidence": confidence,
                    "source": "local_model_enhanced",
                    "bounding_boxes": [d for d in local_detections if any(k in d.get("class", "") for k in self.LOCAL_MODEL_KEYWORDS.get(pest_name, []))]
                }

                if knowledge_match:
                    disease_info["knowledge"] = {
                        "shape": knowledge_match.get("shape", ""),
                        "color": knowledge_match.get("color", ""),
                        "size": knowledge_match.get("size", ""),
                        "symptoms": knowledge_match.get("symptoms", ""),
                        "prevention": knowledge_match.get("prevention", ""),
                        "conditions": knowledge_match.get("conditions", "")
                    }

                merged_diseases.append(disease_info)

            for disease in ai_result.get("diseases", []):
                disease_name = disease.get("name", "")
                if not any(d.get("name") == disease_name for d in merged_diseases):
                    merged_diseases.append(disease)
        else:
            merged_diseases = ai_result.get("diseases", [])

        return {
            "crop_type": ai_result.get("crop_type", ""),
            "has_pest": len(merged_diseases) > 0,
            "diseases": merged_diseases,
            "local_detections": local_detections if has_local_detection else [],
            "analysis_notes": ai_result.get("analysis_notes", "")
        }

    async def should_trigger_review(self, detection_result: Dict[str, Any]) -> bool:
        """判断是否需要触发智能体审查"""
        if not detection_result.get("has_pest"):
            return False

        merged_result = detection_result.get("merged_result", {})
        diseases = merged_result.get("diseases", [])

        for disease in diseases:
            confidence = disease.get("confidence", 0)
            severity = disease.get("severity", "low")

            if confidence >= 0.8 or severity in ["high", "critical"]:
                return True

        return False


detection_router = DetectionRouter()
