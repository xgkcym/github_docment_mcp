import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("http://127.0.0.1:7860/gradio_api/mcp/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for tool in tools.tools:
                print(tool.name)
                print(tool.description)
            print(f"✅ 成功！找到 {len(tools.tools)} 个工具")

asyncio.run(main())