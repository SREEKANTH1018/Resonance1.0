import asyncio
from dotenv import load_dotenv
load_dotenv()

async def main():
    from app.integrations.ai_engine_client import AIEngineClient
    result = await AIEngineClient().decision({
        "text": "ARGUS integration health check",
        "sources": [],
        "iteration": 1,
    })
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
