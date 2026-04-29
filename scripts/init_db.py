#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建表结构和初始数据
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import text
from app.core.config import settings
from app.models.database import engine, Base
from app.models.models import (
    User, Detection, TrackingTask, TrackingUpdate, ModelRegistry,
    Notification, KnowledgeBase, VideoFrame, ApiKey, OperationLog, Conversation
)


async def create_tables():
    """创建所有表"""
    print("正在创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表创建完成!")


async def insert_initial_data():
    """插入初始数据"""
    from app.models.database import async_session
    from app.core.security import get_password_hash

    async with async_session() as session:
        try:
            admin = User(
                id="550e8400-e29b-41d4-a716-446655440000",
                username="admin",
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                role="admin"
            )
            session.add(admin)

            default_models = [
                ModelRegistry(
                    model_name="rice-pest-yolov8",
                    model_version="v1.0",
                    model_path="models/rice-pest-yolov8.pt",
                    supported_pests=["稻飞虱", "二化螟", "三化螟", "稻纵卷叶螟"],
                    supported_crops=["水稻"],
                    is_active=True,
                    is_default=True,
                    metrics={"mAP": 0.92, "precision": 0.89, "recall": 0.91}
                ),
                ModelRegistry(
                    model_name="corn-disease-yolov8",
                    model_version="v1.0",
                    model_path="models/corn-disease-yolov8.pt",
                    supported_pests=["大斑病", "小斑病", "锈病"],
                    supported_crops=["玉米"],
                    is_active=True,
                    metrics={"mAP": 0.89, "precision": 0.87, "recall": 0.88}
                )
            ]
            for model in default_models:
                session.add(model)

            sample_knowledge = [
                KnowledgeBase(
                    disease_name="稻飞虱",
                    crop_type="水稻",
                    symptoms="叶片变黄，植株矮小，严重时整株枯死。基部叶鞘可见黄褐色斑点，后扩大成云纹状斑块。",
                    conditions="喜温暖潮湿环境，适宜温度25-30℃。多发生在水稻生长中后期，尤其是孕穗至抽穗阶段。主要通过气流远距离迁飞传播。",
                    prevention="农业防治：选用抗虫品种，合理施肥，避免偏施氮肥。物理防治：利用趋光性，可用黑光灯诱杀。化学防治：可用吡蚜酮、噻虫嗪等药剂喷雾防治。",
                    cases="2024年某水稻种植基地，在水稻抽穗期发现大量稻飞虱危害。经及时采用吡蚜酮进行喷雾防治，并结合田间管理，有效控制了虫情。"
                ),
                KnowledgeBase(
                    disease_name="水稻纹枯病",
                    crop_type="水稻",
                    symptoms="叶片出现暗绿色水渍状小斑，后扩大成云纹状或虎纹状病斑。病斑边缘褐色，中央灰白色至淡褐色。",
                    conditions="高温高湿条件下易发病。发病温度范围20-32℃，最适温度28-32℃。田间湿度大、氮肥施用过多、种植密度过大会加重发病。",
                    prevention="农业防治：合理密植，增施磷钾肥，及时排除田间积水。化学防治：可用井冈霉素、枯草芽孢杆菌等生物制剂喷雾防治。",
                    cases="某农场采用无人机喷洒井冈霉素，有效控制了纹枯病的蔓延，产量损失降低到5%以下。"
                )
            ]
            for kb in sample_knowledge:
                session.add(kb)

            await session.commit()
            print("初始数据插入完成!")
        except Exception as e:
            await session.rollback()
            print(f"插入初始数据时出错: {e}")


async def init_database():
    """初始化数据库"""
    print("=" * 50)
    print("病虫害检测系统 - 数据库初始化")
    print("=" * 50)
    print(f"数据库地址: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    print()

    try:
        await create_tables()
        await insert_initial_data()
        print()
        print("数据库初始化完成!")
        print("=" * 50)
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database())
