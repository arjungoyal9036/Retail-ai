import httpx
from fastapi import HTTPException


async def request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    params: dict[str, object] | None = None,
    json_body: dict[str, object] | None = None,
) -> dict[str, object]:
    try:
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=5.0) as client:
            response = await client.request(method, path, params=params, json=json_body)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="A dependent service timed out.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="A dependent service is unavailable.") from exc

    if not response.is_success:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        detail = payload.get("detail", "A dependent service returned an error.")
        raise HTTPException(status_code=response.status_code, detail=detail)

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="A dependent service returned invalid data.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="A dependent service returned invalid data.")
    return payload
