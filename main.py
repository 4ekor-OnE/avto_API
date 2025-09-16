from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests

# Создаем основное приложение FastAPI
app = FastAPI(title="FIAS Proxy API")

# Настраиваем CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше указать конкретные домены
    allow_methods=["*"],
    allow_headers=["*"],
)

# Базовый URL FIAS API
FIAS_BASE_URL = "https://fias.keydisk.ru/api/address"

# Функция для форматирования полного адреса из полученных данных
def format_full_address(fias_obj):
    """Собираем полный адрес из компонентов"""
    parts = []

    # Добавляем регион если есть
    region = fias_obj.get("region", {})
    if region.get("formalName"):
        parts.append(f"{region.get('formalName')} {region.get('shortName','')}")

    # Добавляем город
    city = fias_obj.get("city", {})
    if city.get("formalName"):
        parts.append(f"г. {city.get('formalName')}")

    # Добавляем поселок/деревню/село
    settlement = fias_obj.get("place", {})
    if settlement.get("formalName"):
        parts.append(f"{settlement.get('shortName','')} {settlement.get('formalName')}".strip())

    # Добавляем улицу
    street = fias_obj.get("street", {})
    if street.get("formalName"):
        parts.append(f"ул. {street.get('formalName')}")

    # Добавляем дом
    house = fias_obj.get("house", {})
    if house.get("formalName"):
        parts.append(f"д. {house.get('formalName')}")

    # Добавляем квартиру
    apartment = fias_obj.get("apartment", {})
    if apartment.get("formalName"):
        parts.append(f"кв. {apartment.get('formalName')}")

    return ", ".join(parts)


# Эндпоинт для автодополнения адресов
@app.get("/api/autocomplete")
def autocomplete(query: str = Query(..., min_length=2), limit: int = 10, parentGuid: str = ""):
    """
    Ищем объекты адреса по запросу с учетом родительского GUID.
    Работает для всех уровней: области, города, улицы, дома.
    """
    params = {
        "searchString": query,
        "count": limit,
        "level": "",        # Пустой уровень = поиск по всем уровням
        "parentGuid": parentGuid
    }
    try:
        # Делаем запрос к FIAS API
        resp = requests.get(f"{FIAS_BASE_URL}/FindAddress", params=params)
        resp.raise_for_status()
        data = resp.json()
        
        # Проверяем что получили список
        if not isinstance(data, list):
            return {"error": "Неправильный формат ответа FIAS", "data": data}

        # Возвращаем очищенные данные для фронтенда
        return [
            {
                "fiasGuid": item.get("fiasGuid"),
                "formalName": item.get("formalName", ""),
                "shortName": item.get("shortName", ""),
                "level": item.get("fiaslevel")
            }
            for item in data
        ]
    except requests.RequestException as e:
        return {"error": f"Ошибка запроса к FIAS: {str(e)}"}


# Эндпоинт для поиска полного адреса по GUID
@app.get("/api/search")
def search(guid: str):
    """
    Получаем полный адрес по FIAS GUID любого уровня
    """
    try:
        resp = requests.get(f"{FIAS_BASE_URL}/GetAddressByFiasGuid", params={"guid": guid})
        resp.raise_for_status()
        data = resp.json()
        return {
            "fiasGuid": data.get("fiasGuid"),
            "full_address": format_full_address(data)
        }
    except requests.RequestException as e:
        return {"error": f"Ошибка при получении адреса: {str(e)}"}


# Эндпоинт для получения цепочки адресов
@app.get("/api/get-chain")
def get_chain(guid: str):
    """
    Возвращаем всю иерархию адресов от корня до указанного GUID
    """
    try:
        resp = requests.get(f"{FIAS_BASE_URL}/GetAddressByFiasGuid", params={"guid": guid})
        resp.raise_for_status()
        data = resp.json()
        
        chain = []
        
        # Проходим по всем возможным уровням адреса
        for level_name in ["region", "area", "city", "place", "street", "house", "apartment"]:
            level_data = data.get(level_name, {})
            if level_data.get("formalName"):
                chain.append({
                    "fiasGuid": level_data.get("fiasGuid"),
                    "formalName": level_data.get("formalName"),
                    "shortName": level_data.get("shortName", ""),
                    "level": level_name
                })
        
        return chain
    except requests.RequestException as e:
        return {"error": f"Ошибка при получении цепочки: {str(e)}"}


# Главная страница - отдаем HTML
@app.get("/")
def serve_index():
    return FileResponse("index.html")


# Запуск сервера для разработки
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)