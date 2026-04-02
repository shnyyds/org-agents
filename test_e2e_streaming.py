#!/usr/bin/env python3
"""
端到端流式输出测试
测试从后端到前端的完整流式输出链路
"""
import asyncio
import aiohttp
import json
import time

API_URL = "http://localhost:8000"

async def test_stream_endpoint():
    """测试 /chat/stream 端点的真实流式输出"""
    print("=" * 80)
    print("测试端到端流式输出")
    print("=" * 80)

    payload = {
        "query": "请简单介绍一下你自己",
        "user_id": "test_user",
        "session_id": "test_session",
        "target_agent": "CEO",
        "target_type": "orchestrator",
        "history": []
    }

    print(f"\n发送请求到: {API_URL}/chat/stream")
    print(f"查询: {payload['query']}\n")
    print("-" * 80)

    start_time = time.time()
    chunk_count = 0
    stream_events = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/chat/stream",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    print(f"❌ 请求失败: HTTP {response.status}")
                    return

                print("✅ 连接成功，开始接收流式数据...\n")

                buffer = ""
                async for chunk_bytes in response.content.iter_any():
                    buffer += chunk_bytes.decode('utf-8')
                    lines = buffer.split('\n')
                    buffer = lines.pop()

                    for line in lines:
                        line = line.strip()
                        if not line or not line.startswith('data: '):
                            continue

                        try:
                            data = json.loads(line[6:])
                            chunk_count += 1
                            elapsed = time.time() - start_time

                            if data.get('type') == 'stream':
                                content = data.get('content', '')
                                node = data.get('node', 'unknown')
                                agent = data.get('active_agent', 'unknown')

                                # 实时打印内容
                                print(content, end='', flush=True)

                                # 记录事件
                                stream_events.append({
                                    'type': 'stream',
                                    'time': elapsed,
                                    'node': node,
                                    'agent': agent,
                                    'content_length': len(content)
                                })

                            elif data.get('type') == 'update':
                                agent = data.get('active_agent', 'unknown')
                                print(f"\n\n[{elapsed:.2f}s] 📍 {agent} 节点更新", flush=True)

                            elif data.get('type') == 'final':
                                print(f"\n\n[{elapsed:.2f}s] ✅ 流式输出完成", flush=True)

                            elif data.get('type') == 'error':
                                print(f"\n\n[{elapsed:.2f}s] ❌ 错误: {data.get('message')}", flush=True)

                        except json.JSONDecodeError as e:
                            print(f"\n⚠️  JSON 解析错误: {e}")
                            continue

    except Exception as e:
        print(f"\n❌ 连接错误: {e}")
        return

    print("\n" + "-" * 80)
    print(f"\n📊 统计信息:")
    print(f"  - 总 chunks: {chunk_count}")
    print(f"  - 流式事件: {len(stream_events)}")
    print(f"  - 总耗时: {time.time() - start_time:.2f}秒")

    if stream_events:
        print(f"\n📈 流式事件详情:")
        for i, event in enumerate(stream_events[:10], 1):  # 只显示前10个
            print(f"  {i}. [{event['time']:.2f}s] {event['agent']} - {event['content_length']} 字符")
        if len(stream_events) > 10:
            print(f"  ... 还有 {len(stream_events) - 10} 个事件")

    print("\n" + "=" * 80)

    if len(stream_events) > 5:
        print("✅ 流式输出正常！收到多个实时 chunks")
    elif len(stream_events) > 0:
        print("⚠️  流式输出可能有问题，chunks 数量较少")
    else:
        print("❌ 没有收到流式数据")

if __name__ == "__main__":
    print("\n⚠️  请确保后端服务正在运行: python backend/app/main.py\n")
    asyncio.run(test_stream_endpoint())
