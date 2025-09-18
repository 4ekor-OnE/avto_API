from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests

app = FastAPI(title="FIAS Proxy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIAS_BASE_URL = "https://fias.keydisk.ru/api/address"


@app.get("/api/autocomplete")
def autocomplete(query: str = Query(..., min_length=1), parentGuid: str = "", limit: int = 20):
    """
    Подсказки по адресу.
    parentGuid задаёт контекст (например, выбрана область — дальше будут города этой области).
    """
    params = {
        "searchString": query,
        "count": limit,
        "parentGuid": parentGuid,
        "level": ""
    }
    try:
        r = requests.get(f"{FIAS_BASE_URL}/FindAddress", params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        return [
            {
                "fiasGuid": d.get("fiasGuid"),
                "formalName": d.get("formalName"),
                "shortName": d.get("shortName"),
                "level": str(d.get("fiaslevel"))
            } for d in data
        ]
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/full")
def get_full(guid: str):
    """
    Получаем полную цепочку по GUID (все родители + объект).
    """
    try:
        r = requests.get(f"{FIAS_BASE_URL}/GetAddressByFiasGuid", params={"guid": guid}, timeout=8)
        r.raise_for_status()
        data = r.json()

        result = {
            "address_line": data.get("representation", ""),
            "region": (data.get("region") or {}).get("formalName", ""),
            "city": (data.get("city") or {}).get("formalName", ""),
            "street": (data.get("street") or {}).get("formalName", ""),
            "house": (data.get("house") or {}).get("formalName", ""),
            "apartment": (data.get("apartment") or {}).get("formalName", ""),
            "postal_code": data.get("postalCode") or ""
        }
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def index():
    return FileResponse("index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
