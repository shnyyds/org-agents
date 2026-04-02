#!/usr/bin/env python3
"""
测试脚本：验证模型的真实流式输出
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.llm import get_llm
from langchain_core.messages import HumanMessage
import time

async def test_real_streaming():
    """测试真实的模型流式输出"""
    print("=" * 60)
    print("测试模型真实流式输出")
    print("=" * 60)

    llm = get_llm()

    prompt = [HumanMessage(content="请用一句话介绍你自己")]

    print("\n开始流式输出（每个 chunk 会立即显示）：\n")
    print("-" * 60)

    start_time = time.time()
    chunk_count = 0
    total_content = ""

    async for chunk in llm.astream(prompt):
        chunk_count += 1
        content = chunk.content if hasattr(chunk, 'content') else str(chunk)
        total_content += content

        # 立即打印，不换行
        print(content, end='', flush=True)

        # 显示时间戳（用于验证是真实流式）
        elapsed = time.time() - start_time
        print(f"\n[Chunk {chunk_count} at {elapsed:.2f}s]", end=' ')

    print("\n" + "-" * 60)
    print(f"\n总共接收到 {chunk_count} 个 chunks")
    print(f"总耗时: {time.time() - start_time:.2f}秒")
    print(f"完整内容: {total_content}")
    print("\n" + "=" * 60)

    if chunk_count > 1:
        print("✅ 流式输出正常工作！")
    else:
        print("❌ 流式输出可能有问题，只收到 1 个 chunk")

if __name__ == "__main__":
    asyncio.run(test_real_streaming())
