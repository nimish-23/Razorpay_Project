import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "app.mcp.server"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                "create_payment",
                {
                    "order_id": "ORD-4B1A5FCEFED0"
                },
            )

            print("\nDUPLICATE PAYMENT TEST")
            print("----------------------")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())