import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.services.deepseek_service import deepseek_service


class ReviewAgent:
    """
    自动审查智能体
    基于检测结果触发风险评估和警告推送
    """

    def __init__(self):
        self.deepseek = deepseek_service

    async def review(self, detection_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        执行自动审查

        Args:
            detection_result: 检测结果

        Returns:
            审查结果，包含警告信息（如果需要）
        """
        if not self.should_review(detection_result):
            return None

        context = await self.build_review_context(detection_result)

        risk_assessment = await self.assess_risk(context)

        if risk_assessment.get("is_false_positive"):
            await self.record_false_positive(detection_result, risk_assessment)
            return {
                "status": "false_positive",
                "assessment": risk_assessment
            }

        warning = await self.generate_warning(detection_result, risk_assessment)

        return {
            "status": "warning",
            "warning": warning,
            "risk_assessment": risk_assessment
        }

    def should_review(self, detection_result: Dict[str, Any]) -> bool:
        """
        判断是否需要审查
        触发条件：置信度>80% 或 严重等级为high/critical
        """
        merged_result = detection_result.get("merged_result", {})
        diseases = merged_result.get("diseases", [])

        for disease in diseases:
            confidence = disease.get("confidence", 0)
            severity = disease.get("severity", "low").lower()

            if confidence >= 0.8 or severity in ["high", "critical"]:
                return True

        return False

    async def build_review_context(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """构建审查上下文"""
        context = {
            "detection": result,
            "timestamp": datetime.now().isoformat()
        }

        merged_result = result.get("merged_result", {})
        context["diseases"] = merged_result.get("diseases", [])

        if result.get("ai_analysis"):
            context["ai_analysis"] = result.get("ai_analysis")

        return context

    async def assess_risk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """调用LLM进行风险评估"""
        detection = context.get("detection", {})

        try:
            assessment = await self.deepseek.assess_risk(
                detection_result=detection,
                environment_data=None,
                regional_history=None
            )
            return assessment
        except Exception as e:
            return {
                "risk_level": "medium",
                "risk_score": 0.5,
                "risk_factors": [f"评估服务异常: {str(e)}"],
                "recommendations": ["建议人工确认"],
                "is_false_positive": False,
                "reasoning": "风险评估服务异常，默认中等风险"
            }

    async def record_false_positive(
        self,
        detection_result: Dict[str, Any],
        assessment: Dict[str, Any]
    ):
        """记录误报信息"""
        pass

    async def generate_warning(
        self,
        detection_result: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成警告信息"""
        try:
            warning = await self.deepseek.generate_warning(
                detection_result=detection_result,
                risk_assessment=risk_assessment
            )
            return warning
        except Exception as e:
            diseases = detection_result.get("merged_result", {}).get("diseases", [])
            disease_name = diseases[0].get("name", "未知病虫害") if diseases else "未知病虫害"

            return {
                "title": f"病虫害预警：{disease_name}",
                "content": f"检测到{disease_name}，风险等级：{risk_assessment.get('risk_level', 'medium')}。请及时采取防治措施。",
                "severity": risk_assessment.get("risk_level", "medium"),
                "tags": ["病虫害", "预警"],
                "action_items": risk_assessment.get("recommendations", ["建议人工确认"])
            }

    async def check_regional_alert(
        self,
        detection_result: Dict[str, Any],
        threshold: int = 3,
        days: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        检查是否需要区域预警
        同地区3天内检测到相同病虫害>=3例时触发
        """
        return None


review_agent = ReviewAgent()