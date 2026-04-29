#!/usr/bin/env python3
"""测试数据库连接"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.models.database import async_session
from sqlalchemy import text


async def test_connection():
    print("测试数据库连接...")
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ 数据库连接成功!")
                return True
            else:
                print("❌ 数据库查询结果异常")
                return False
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


async def test_tables():
    print("检查数据库表...")
    try:
        async with async_session() as session:
            result = await session.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            print(f"找到 {len(tables)} 个表:")
            for table in tables:
                print(f"  - {table[0]}")
            return True
    except Exception as e:
        print(f"❌ 检查表失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        asyncio.run(test_tables())
