from .config import config

class RetrievalClient:
    # Tavily adapter. If no key is configured, it reports unavailable explicitly.

    async def search(self, query):
        if not config.tavily_api_key:
            return {"enabled": False, "query": query, "results": [],
                    "reason": "TAVILY_API_KEY is not configured"}
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=config.tavily_api_key)
        response = await client.search(
            query,
            max_results=config.tavily_max_results,
            include_raw_content=True,
        )
        return {"enabled": True, "query": query, "results": response.get("results", [])}

    async def extract(self, url):
        if not config.tavily_api_key:
            return {"enabled": False, "url": url, "results": [],
                    "reason": "TAVILY_API_KEY is not configured"}
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=config.tavily_api_key)
        response = await client.extract(url)
        return {"enabled": True, "url": url, "results": response.get("results", [])}
