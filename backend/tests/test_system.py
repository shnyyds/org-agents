import asyncio
import httpx
import json

async def test_full_system():
    url = "http://localhost:8000/chat"
    
    test_queries = [
        {
            "name": "Market Analysis",
            "query": "分析一下电梯行业的市场趋势",
            "user_id": "test_1"
        },
        {
            "name": "Tech Pipeline",
            "query": "帮我开发一个电梯监控系统的 API 接口",
            "user_id": "test_2"
        },
        {
            "name": "Sales & Repair Trigger",
            "query": "我需要购买 5 台智能电梯，请给我报价并安排安装",
            "user_id": "test_3"
        }
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        for test in test_queries:
            print(f"\n--- Testing: {test['name']} ---")
            print(f"Query: {test['query']}")
            try:
                response = await client.post(url, json={
                    "query": test["query"],
                    "user_id": test["user_id"]
                })
                result = response.json()
                print(f"Status: {result.get('status')}")
                print(f"Department: {result.get('department')}")
                print(f"Intent: {result.get('intent')}")
                print(f"Response: {result.get('response')[:200]}...")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    print("Starting system integrity test...")
    print("Note: Ensure the backend is running at http://localhost:8000")
    asyncio.run(test_full_system())
