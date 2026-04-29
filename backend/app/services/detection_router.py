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
        use_local_model: bool = True,
        force_cloud_only: bool = False
    ) -> Dict[str, Any]:
        """
        执行智能检测路由
        """
        ai_result = await self._cloud_ai_analyze(image_url)

        if not ai_result or ai_result.get("error"):
            return {
                "source": DetectionSource.CLOUD_AI,
                "ai_analysis": ai_result,
                "has_pest": None,
                "knowledge_match": None,
                "local_detection": None,
                "matched_models": [],
                "confirmed_no_pest": False
            }

        has_pest_ai = ai_result.get("has_pest", False)
        no_pest_confidence = ai_result.get("no_pest_confidence", 0)

        matched_pests = self._match_pests_from_ai(ai_result)

        if force_cloud_only or not use_local_model:
            return {
                "source": DetectionSource.CLOUD_AI,
                "ai_analysis": ai_result,
                "has_pest": has_pest_ai,
                "knowledge_match": None,
                "local_detection": None,
                "matched_models": matched_pests,
                "confirmed_no_pest": False
            }

        model_key = self._select_best_model(matched_pests)
        local_result = await self._local_model_detect(image_url, model_key)

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
                        "matched_models": matched_pests,
                        "confirmed_no_pest": True,
                        "message": "经AI与知识库综合分析，确认图像中无病虫害"
                    }

        merged_result = self._merge_results(ai_result, local_result, knowledge_match)

        return {
            "source": DetectionSource.LOCAL_MODEL if has_local_detection else DetectionSource.CLOUD_AI,
            "ai_analysis": ai_result,
            "has_pest": has_local_detection or has_pest_ai,
            "knowledge_match": knowledge_match,
            "local_detection": local_result,
            "matched_models": matched_pests,
            "confirmed_no_pest": confirmed_no_pest,
            "merged_result": merged_result
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
