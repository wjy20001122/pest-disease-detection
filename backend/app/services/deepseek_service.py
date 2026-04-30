import httpx
import json
import base64
from typing import Optional, List, Dict, Any
from app.core.config import settings


class DeepSeekService:
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        content = await self.chat(messages, temperature, max_tokens)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON response", "raw_content": content}

    async def ask_pest_question(self, question: str, context: str = "") -> str:
        system_prompt = """你是一个专业的农作物病虫害识别和防治专家。请根据用户的问题，给出准确、专业的回答。

回答要求：
1. 识别用户描述的病虫害症状
2. 提供可能的原因和发生条件
3. 给出具体的防治方法和建议
4. 回答要专业、清晰、易懂

如果用户的问题与病虫害无关，请礼貌地引导用户咨询相关领域专家。"""

        user_content = question
        if context:
            user_content = f"参考知识：\n{context}\n\n用户问题：{question}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return await self.chat(messages, temperature=0.5)

    async def ask_with_context(
        self,
        question: str,
        context: str = "",
        sources: list = None
    ) -> str:
        """结合知识库上下文进行问答（RAG）

        Args:
            question: 用户问题
            context: 知识库检索到的上下文
            sources: 知识库来源条目
        """
        system_prompt = """你是一个专业的农作物病虫害识别和防治专家。你的任务是结合提供的知识库信息，准确回答用户的问题。

回答要求：
1. 结合知识库中的具体信息进行回答
2. 病虫害识别要包含：名称、形状特征、颜色特征
3. 防治建议要具体、可操作
4. 如果知识库中有相似案例，优先参考
5. 回答要专业、清晰、语言通俗易懂

参考知识库格式：
- 作物类型：玉米/小麦/水稻
- 类别：虫害/病害
- 形状特征：如椭圆形、蠕虫形、梭形等
- 颜色特征：如黄绿色、灰褐色等
- 症状：具体表现
- 发生条件：适宜的温度、湿度等
- 防治方法：农业防治、化学防治、生物防治等"""

        user_content = question
        if context:
            user_content = f"【知识库参考信息】\n{context}\n\n【用户问题】\n{question}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return await self.chat(messages, temperature=0.5)

    async def assess_risk(
        self,
        detection_result: Dict[str, Any],
        environment_data: Dict[str, Any] = None,
        regional_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """评估检测结果的风险等级

        Args:
            detection_result: 检测结果
            environment_data: 环境数据（天气、温度、湿度等）
            regional_history: 地区历史检测记录
        """
        system_prompt = """你是一个农业病虫害风险评估专家。请根据提供的检测结果和环境信息，评估病虫害的风险等级。

评估维度：
1. 病虫害置信度
2. 严重程度
3. 环境条件是否有利于病虫害扩散
4. 同地区历史发生情况

请返回JSON格式：
{
    "risk_level": "low/medium/high/critical",
    "risk_score": 0.85,
    "risk_factors": ["风险因素1", "风险因素2"],
    "recommendations": ["建议1", "建议2"],
    "is_false_positive": false,
    "reasoning": "风险评估的详细解释"
}"""

        context_parts = [f"检测结果：{json.dumps(detection_result, ensure_ascii=False)}"]

        if environment_data:
            context_parts.append(f"环境数据：{json.dumps(environment_data, ensure_ascii=False)}")

        if regional_history:
            context_parts.append(f"地区历史（最近7天）：{json.dumps(regional_history[:10], ensure_ascii=False)}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n\n".join(context_parts)}
        ]

        result = await self.chat_json(messages, temperature=0.2)
        return result

    async def generate_warning(
        self,
        detection_result: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成警告信息"""
        system_prompt = """你是一个农业病虫害预警信息生成专家。请根据检测结果和风险评估，生成一条清晰的预警信息。

预警信息要求：
1. 标题简洁明了
2. 内容包含病虫害名称、风险等级、建议措施
3. 语言通俗易懂，适合农户阅读
4. 包含必要的安全提示

请返回JSON格式：
{
    "title": "预警标题",
    "content": "预警内容正文",
    "severity": "low/medium/high/critical",
    "tags": ["标签1", "标签2"],
    "action_items": ["需要采取的行动1", "行动2"]
}"""

        context = f"""检测结果：{json.dumps(detection_result, ensure_ascii=False)}
风险评估：{json.dumps(risk_assessment, ensure_ascii=False)}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]

        result = await self.chat_json(messages, temperature=0.3)
        return result

    async def generate_prevention_advice(self, disease_name: str, conditions: str) -> str:
        system_prompt = """你是一个专业的农业技术专家。请为以下病虫害生成详细的防治方案。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"病虫害名称：{disease_name}\n发生条件：{conditions}\n\n请提供：\n1. 农业防治措施\n2. 化学防治药剂推荐\n3. 最佳防治时期\n4. 预防措施"}
        ]

        return await self.chat(messages, temperature=0.6)

    async def analyze_image_url(self, image_url: str) -> Dict[str, Any]:
        """分析图像URL，识别病虫害

        Args:
            image_url: 图像的OSS URL

        Returns:
            包含分析结果的字典
        """
        system_prompt = """你是一个农作物病虫害识别专家。请分析用户上传的作物图像，识别可能存在的病虫害。

输出格式（必须返回JSON）：
{
    "crop_type": "作物类型",
    "has_pest": true/false,
    "no_pest_confidence": 0.0-1.0,
    "diseases": [
        {
            "name": "病虫害名称",
            "confidence": 0.0-1.0,
            "severity": "low/medium/high",
            "symptoms": "症状描述",
            "possible_causes": "可能原因",
            "prevention": "防治建议"
        }
    ],
    "model_match_keywords": ["关键词1", "关键词2"],
    "analysis_notes": "分析备注"
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析这张图像：{image_url}"}
        ]

        result = await self.chat_json(messages, temperature=0.3)
        return result

    async def analyze_with_detection_context(
        self,
        image_url: str,
        detection_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于本地检测结构结果生成AI分析建议（不改本地判定）"""
        system_prompt = """你是农业病虫害诊断专家。请基于“本地模型检测结果”和图像URL生成辅助分析建议。

要求：
1. 不要否定本地检测是否命中，只做风险与防治补充；
2. 结合本地模型类别、数量、置信度、框信息，给出更可执行建议；
3. 返回严格JSON。

输出格式：
{
    "crop_type": "作物类型",
    "has_pest": true,
    "no_pest_confidence": 0.0,
    "diseases": [
        {
            "name": "病虫害名称",
            "confidence": 0.0-1.0,
            "severity": "low/medium/high",
            "symptoms": "症状描述",
            "possible_causes": "可能原因",
            "prevention": "防治建议"
        }
    ],
    "model_match_keywords": ["关键词1", "关键词2"],
    "analysis_notes": "说明该建议基于本地检测结构结果生成"
}"""

        payload = {
            "image_url": image_url,
            "local_detection_context": detection_context,
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ]
        result = await self.chat_json(messages, temperature=0.2)
        return result

    async def confirm_no_pest(self, image_url: str, initial_result: Dict[str, Any]) -> bool:
        """二次确认是否真的无病虫害

        Args:
            image_url: 图像URL
            initial_result: 初次AI分析结果

        Returns:
            True 表示确认无病虫害，False 表示可能有病虫害
        """
        system_prompt = """你是一个农作物病虫害识别专家。用户在本地模型中未检测到病虫害，请重新仔细分析图像，确认是否真的无病虫害。

判断标准：
1. 仔细检查叶片、茎秆、果实等部位是否有异常
2. 检查是否有虫害痕迹（孔洞、咬痕、分泌物等）
3. 检查是否有病斑、变色、畸形等病害特征

请返回JSON格式：
{
    "confirmed_no_pest": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "判断理由",
    "any_suspicious_signs": ["可疑迹象1", "可疑迹象2"] 或 []
}"""

        context = f"初次分析结果：{json.dumps(initial_result, ensure_ascii=False)}\n\n图像URL：{image_url}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]

        result = await self.chat_json(messages, temperature=0.2)
        return result.get("confirmed_no_pest", False)


deepseek_service = DeepSeekService()
