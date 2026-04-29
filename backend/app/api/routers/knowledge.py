from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.deepseek_service import deepseek_service

router = APIRouter(prefix="/knowledge", tags=["知识库"])


knowledge_db = [
    {
        "id": 1,
        "title": "蚜虫的识别与防治",
        "disease_name": "蚜虫",
        "crop_type": "玉米",
        "category": "虫害",
        "shape": "椭圆形",
        "color": "黄绿色/绿色",
        "size": "体长2-3mm",
        "symptoms": "叶片卷曲、发黄，茎秆变形，植株生长受阻。大量发生时可见蜜露分泌，引起煤污病。",
        "conditions": "温暖干燥环境适宜繁殖，适宜温度20-28℃。春秋季高发。",
        "prevention": "农业防治：清除田间杂草，合理密植。化学防治：可用吡虫啉、啶虫脒等药剂喷雾。生物防治：释放瓢虫、草蛉等天敌。",
        "tags": ["蚜虫", "虫害", "防治", "玉米"],
        "updated_at": "2026-04-25"
    },
    {
        "id": 2,
        "title": "玉米粘虫幼虫的危害与防治",
        "disease_name": "玉米粘虫幼虫",
        "crop_type": "玉米",
        "category": "虫害",
        "shape": "蠕虫形/圆柱形",
        "color": "灰绿色/黄绿色",
        "size": "体长30-50mm",
        "symptoms": "叶片被啃食成缺刻，严重时吃光叶片，仅剩叶脉。幼虫白天潜伏，夜间取食，具有暴食性。",
        "conditions": "喜温暖潮湿，适宜温度22-28℃。暴食性害虫，发生量大时可在短期内将叶片吃光。",
        "prevention": "农业防治：深耕灭蛹，清除杂草。物理防治：点灯诱杀成虫。化学防治：可用氯虫苯甲酰胺、甲维盐等药剂喷雾。",
        "tags": ["粘虫", "玉米粘虫", "虫害", "玉米"],
        "updated_at": "2026-04-24"
    },
    {
        "id": 3,
        "title": "玉米螟的识别与综合防治",
        "disease_name": "玉米螟幼虫",
        "crop_type": "玉米",
        "category": "虫害",
        "shape": "蠕虫形",
        "color": "灰白色/淡粉色",
        "size": "体长20-30mm",
        "symptoms": "叶片出现排孔，茎秆被蛀食，造成风折。心叶期受害最重，影响玉米生长发育。",
        "conditions": "温度24-28℃，相对湿度60%以上适宜发生。主要危害玉米心叶期和穗期。",
        "prevention": "农业防治：选用抗虫品种，处理秸秆消灭越冬幼虫。生物防治：释放赤眼蜂。化学防治：心叶期可用辛硫磷颗粒剂灌心。",
        "tags": ["玉米螟", "螟虫", "虫害", "玉米"],
        "updated_at": "2026-04-23"
    },
    {
        "id": 4,
        "title": "玉米螟成虫的生物学特性与防治",
        "disease_name": "玉米螟成虫",
        "crop_type": "玉米",
        "category": "虫害",
        "shape": "蛾形",
        "color": "黄褐色/淡黄色",
        "size": "翅展20-35mm",
        "symptoms": "成虫本身不直接危害，但会产卵繁殖后代。卵块多产于叶片背面，孵化后幼虫钻入茎秆危害。",
        "conditions": "夜间活动，有强趋光性。高温高湿条件下繁殖快。",
        "prevention": "物理防治：点灯诱杀成虫。农业防治：秸秆还田时粉碎杀死越冬幼虫。生物防治：释放赤眼蜂控制卵块。",
        "tags": ["玉米螟", "成虫", "虫害", "玉米"],
        "updated_at": "2026-04-26"
    },
    {
        "id": 5,
        "title": "玉米大斑病的识别与防治",
        "disease_name": "玉米大斑病",
        "crop_type": "玉米",
        "category": "病害",
        "shape": "长梭形/条斑形",
        "color": "灰褐色/褐色",
        "size": "病斑长5-15cm，宽1-3cm",
        "symptoms": "叶片上出现椭圆形或长梭形灰褐色病斑，后变为褐色，潮湿时产生黑色霉层。严重时叶片枯死。",
        "conditions": "低温高湿适宜发病，20-25℃多雨高湿条件下流行。",
        "prevention": "农业防治：选用抗病品种，合理密植。化学防治：可用多菌灵、甲基托布津等药剂喷雾。",
        "tags": ["大斑病", "病害", "玉米"],
        "updated_at": "2026-04-22"
    },
    {
        "id": 6,
        "title": "玉米小斑病的识别与防治",
        "disease_name": "玉米小斑病",
        "crop_type": "玉米",
        "category": "病害",
        "shape": "椭圆形/近圆形",
        "color": "黄褐色/红褐色",
        "size": "病斑长1-2cm，宽0.5-1cm",
        "symptoms": "叶片上出现椭圆形或近圆形黄褐色小斑，后变为红褐色，边缘清晰。病斑可相互愈合。",
        "conditions": "高温高湿发病，26-32℃多雨季节高发。",
        "prevention": "农业防治：清除病残体，合理施肥。化学防治：可用代森锰锌、百菌清等药剂喷雾。",
        "tags": ["小斑病", "病害", "玉米"],
        "updated_at": "2026-04-21"
    },
    {
        "id": 7,
        "title": "小麦蚜虫的识别与防治",
        "disease_name": "小麦蚜虫",
        "crop_type": "小麦",
        "category": "虫害",
        "shape": "椭圆形",
        "color": "绿色/黄绿色/黑色",
        "size": "体长1.5-2.5mm",
        "symptoms": "叶片黄化卷曲，穗期危害麦粒，造成减产。分泌蜜露引起煤污病，传播病毒病。",
        "conditions": "温暖干燥环境，20-25℃适宜繁殖。穗期危害最重。",
        "prevention": "农业防治：合理密植，加强田间管理。化学防治：可用吡虫啉、啶虫脒喷雾。生物防治：释放瓢虫。",
        "tags": ["蚜虫", "虫害", "小麦"],
        "updated_at": "2026-04-20"
    },
    {
        "id": 8,
        "title": "小麦粘虫的识别与防治",
        "disease_name": "小麦粘虫",
        "crop_type": "小麦",
        "category": "虫害",
        "shape": "蠕虫形",
        "color": "灰绿色/暗绿色",
        "size": "体长20-35mm",
        "symptoms": "叶片被啃食成缺刻，严重时吃光叶片。幼虫受惊后吐丝下垂，有假死性。",
        "conditions": "喜温暖潮湿，春季发生量大，4-5月危害最重。",
        "prevention": "农业防治：深耕灭蛹，清除杂草。物理防治：糖醋液诱杀成虫。化学防治：可用氯虫苯甲酰胺喷雾。",
        "tags": ["粘虫", "虫害", "小麦"],
        "updated_at": "2026-04-19"
    },
    {
        "id": 9,
        "title": "小麦吸浆虫的识别与防治",
        "disease_name": "小麦吸浆虫",
        "crop_type": "小麦",
        "category": "虫害",
        "shape": "纺锤形/橙红色",
        "color": "橙红色/桔黄色",
        "size": "体长2-3mm",
        "symptoms": "幼虫吸食小麦颖果浆液，造成瘪粒、空粒。受害麦粒呈红褐色。",
        "conditions": "潮湿低洼地发生严重，小麦抽穗至扬花期危害最大。",
        "prevention": "农业防治：选用抗虫品种，深翻土地。化学防治：小麦抽穗期可用倍硫磷喷雾。",
        "tags": ["吸浆虫", "虫害", "小麦"],
        "updated_at": "2026-04-18"
    },
    {
        "id": 10,
        "title": "小麦赤霉病的识别与防治",
        "disease_name": "小麦赤霉病",
        "crop_type": "小麦",
        "category": "病害",
        "shape": "不规则形/斑片状",
        "color": "粉红色/橙红色霉层",
        "size": "病斑大小不一，可覆盖整个穗部",
        "symptoms": "穗部出现粉红色或橙红色霉层，籽粒干瘪、皱缩，表面有白色或粉红色霉层。",
        "conditions": "扬花期遇阴雨天气，温度15-25℃，湿度>80%发病严重。",
        "prevention": "农业防治：选用抗病品种，合理排灌。化学防治：抽穗期可用多菌灵、甲基托布津喷雾。",
        "tags": ["赤霉病", "病害", "小麦"],
        "updated_at": "2026-04-17"
    },
    {
        "id": 11,
        "title": "小麦白粉病的识别与防治",
        "disease_name": "小麦白粉病",
        "crop_type": "小麦",
        "category": "病害",
        "shape": "圆形/椭圆形霉斑",
        "color": "白色/灰白色粉末状霉层",
        "size": "病斑直径1-10mm，可相互愈合",
        "symptoms": "叶片表面出现白色或灰白色粉末状霉层，后期霉层变为灰褐色，产生黑色小点。",
        "conditions": "15-20℃发病，湿度大、通风不良地块发病重。",
        "prevention": "农业防治：选用抗病品种，合理密植。化学防治：可用三唑酮、烯唑醇等药剂喷雾。",
        "tags": ["白粉病", "病害", "小麦"],
        "updated_at": "2026-04-16"
    },
    {
        "id": 12,
        "title": "小麦锈病的识别与防治",
        "disease_name": "小麦锈病",
        "crop_type": "小麦",
        "category": "病害",
        "shape": "条状/夏孢子堆",
        "color": "黄褐色/红褐色铁锈状",
        "size": "条锈病斑沿叶脉排列成条状",
        "symptoms": "叶片或茎秆出现黄褐色或红褐色铁锈状孢子堆，隆起破裂后散出锈色粉末。",
        "conditions": "条锈15-20℃，叶锈15-25℃，杆锈20-25℃发病。潮湿多雨发病重。",
        "prevention": "农业防治：选用抗病品种，加强田间管理。化学防治：可用三唑酮、丙环唑等药剂喷雾。",
        "tags": ["锈病", "病害", "小麦"],
        "updated_at": "2026-04-15"
    },
    {
        "id": 13,
        "title": "稻飞虱的识别与防治",
        "disease_name": "稻飞虱",
        "crop_type": "水稻",
        "category": "虫害",
        "shape": "长椭圆形/纺锤形",
        "color": "灰褐色/黄褐色/白色",
        "size": "体长2-5mm",
        "symptoms": "叶片黄化，植株矮小，分蘖减少。严重时造成倒伏，颗粒无收。伤口分泌蜜露引起煤污病。",
        "conditions": "高温高湿，25-28℃适宜繁殖。孕穗至灌浆期危害最大。",
        "prevention": "农业防治：合理密植，加强田间管理。化学防治：可用噻虫嗪、吡虫啉等药剂喷雾。",
        "tags": ["稻飞虱", "虫害", "水稻"],
        "updated_at": "2026-04-14"
    },
    {
        "id": 14,
        "title": "稻纵卷叶螟的识别与防治",
        "disease_name": "稻纵卷叶螟",
        "crop_type": "水稻",
        "category": "虫害",
        "shape": "蛾形/幼虫蠕虫形",
        "color": "黄绿色/淡绿色",
        "size": "成虫翅展15-20mm，幼虫20-30mm",
        "symptoms": "幼虫吐丝将叶片卷成筒状，啃食叶肉留下表皮，形成白条斑。",
        "conditions": "喜高温高湿，28-32℃适宜繁殖。分蘖期和穗期危害最大。",
        "prevention": "农业防治：深耕灭蛹，清除杂草。物理防治：灯光诱杀成虫。化学防治：可用氯虫苯甲酰胺、苏云金杆菌。",
        "tags": ["卷叶螟", "虫害", "水稻"],
        "updated_at": "2026-04-13"
    },
    {
        "id": 15,
        "title": "二化螟的识别与防治",
        "disease_name": "二化螟",
        "crop_type": "水稻",
        "category": "虫害",
        "shape": "蛾形/幼虫圆柱形",
        "color": "灰褐色/黄褐色",
        "size": "翅展20-35mm",
        "symptoms": "幼虫钻入茎秆危害，造成枯心苗、枯孕穗、白穗。茎秆易折断。",
        "conditions": "温度18-25℃，相对湿度80%以上适宜发生。",
        "prevention": "农业防治：选用抗虫品种，处理稻草。生物防治：释放赤眼蜂。化学防治：可用杀虫双、氟虫腈。",
        "tags": ["二化螟", "虫害", "水稻"],
        "updated_at": "2026-04-12"
    },
    {
        "id": 16,
        "title": "稻瘟病的识别与防治",
        "disease_name": "稻瘟病",
        "crop_type": "水稻",
        "category": "病害",
        "shape": "梭形/椭圆形病斑",
        "color": "灰白色/灰绿色/褐色",
        "size": "病斑大小2-10mm",
        "symptoms": "叶片出现梭形或椭圆形灰白色病斑，边缘褐色。穗颈发病造成白穗，节部发病造成节变黑。",
        "conditions": "温度25-28℃，湿度>90%发病严重。阴雨连绵、日照不足发病重。",
        "prevention": "农业防治：选用抗病品种，合理施肥。化学防治：可用三环唑、稻瘟灵等药剂喷雾。",
        "tags": ["稻瘟病", "病害", "水稻"],
        "updated_at": "2026-04-11"
    },
    {
        "id": 17,
        "title": "水稻纹枯病的识别与防治",
        "disease_name": "水稻纹枯病",
        "crop_type": "水稻",
        "category": "病害",
        "shape": "云纹状/波浪形",
        "color": "灰绿色/暗绿色",
        "size": "病斑可蔓延至整个叶鞘",
        "symptoms": "叶鞘出现灰绿色云纹状病斑，后期产生白色菌丝团，形成暗褐色菌核。",
        "conditions": "高温高湿，28-32℃发病最重。分蘖盛期至抽穗期发病严重。",
        "prevention": "农业防治：浅水灌溉，合理施肥。化学防治：可用井冈霉素、苯醚甲环唑等药剂。",
        "tags": ["纹枯病", "病害", "水稻"],
        "updated_at": "2026-04-10"
    },
    {
        "id": 18,
        "title": "水稻白叶枯病的识别与防治",
        "disease_name": "水稻白叶枯病",
        "crop_type": "水稻",
        "category": "病害",
        "shape": "条斑型/叶缘型",
        "color": "灰白色/黄白色",
        "size": "病斑从叶尖或叶缘开始向下延伸",
        "symptoms": "叶片叶尖或叶缘出现黄绿色或灰绿色条斑，后变为灰白色枯死。潮湿时有黄色菌脓。",
        "conditions": "暴雨或洪涝后发病重，26-30℃发病。台风暴雨造成伤口利于侵入。",
        "prevention": "农业防治：选用抗病品种，加强田间管理。化学防治：可用叶枯唑、噻森铜等药剂喷雾。",
        "tags": ["白叶枯病", "病害", "水稻"],
        "updated_at": "2026-04-09"
    }
]


def search_knowledge(
    keyword: str = "",
    crop_type: str = None,
    category: str = None,
    shape: str = None,
    color: str = None
) -> List[dict]:
    """根据多条件搜索知识库"""
    results = knowledge_db

    if keyword:
        keyword_lower = keyword.lower()
        results = [
            item for item in results
            if keyword_lower in item.get("title", "").lower()
            or keyword_lower in item.get("disease_name", "").lower()
            or keyword_lower in item.get("symptoms", "").lower()
            or keyword_lower in item.get("tags", [])
        ]

    if crop_type:
        results = [item for item in results if item.get("crop_type") == crop_type]

    if category:
        results = [item for item in results if item.get("category") == category]

    if shape:
        shape_lower = shape.lower()
        results = [
            item for item in results
            if shape_lower in item.get("shape", "").lower()
        ]

    if color:
        color_lower = color.lower()
        results = [
            item for item in results
            if color_lower in item.get("color", "").lower()
        ]

    return results


@router.get("/search")
async def search(
    keyword: str = Query(""),
    crop_type: str = Query(None, description="作物类型：玉米/小麦/水稻"),
    category: str = Query(None, description="类别：虫害/病害"),
    shape: str = Query(None, description="形状特征"),
    color: str = Query(None, description="颜色特征"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50)
):
    results = search_knowledge(keyword, crop_type, category, shape, color)

    offset = (page - 1) * page_size
    items = results[offset:offset + page_size]

    return {
        "items": items,
        "total": len(results),
        "page": page,
        "page_size": page_size
    }


@router.get("/recent")
async def get_recent(
    page_size: int = Query(5, ge=1, le=20)
):
    sorted_items = sorted(knowledge_db, key=lambda x: x.get("updated_at", ""), reverse=True)
    return {
        "items": sorted_items[:page_size]
    }


@router.get("/crops")
async def get_crops():
    """获取所有作物类型"""
    crops = list(set(item["crop_type"] for item in knowledge_db))
    return {"crops": crops}


@router.get("/categories")
async def get_categories():
    """获取所有类别"""
    categories = list(set(item["category"] for item in knowledge_db))
    return {"categories": categories}


@router.get("/shapes")
async def get_shapes():
    """获取所有形状特征"""
    shapes = list(set(item["shape"] for item in knowledge_db))
    return {"shapes": shapes}


@router.get("/colors")
async def get_colors():
    """获取所有颜色特征"""
    colors = list(set(item["color"] for item in knowledge_db))
    return {"colors": colors}


@router.get("/{item_id}")
async def get_item(
    item_id: int
):
    for item in knowledge_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="知识条目不存在")
