import httpx

class IntegrationHTTPError(RuntimeError):
    pass

async def post_json(url, payload, *, api_key="", timeout=60):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise IntegrationHTTPError(f"Integration request failed: {exc}") from exc
    if response.status_code >= 400:
        raise IntegrationHTTPError(
            f"Integration returned HTTP {response.status_code}: {response.text[:500]}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise IntegrationHTTPError("Integration returned non-JSON data") from exc
