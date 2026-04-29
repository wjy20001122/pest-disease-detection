from fastapi import APIRouter, Query
from app.services.environment_service import environment_service

router = APIRouter(prefix="/environment", tags=["环境数据"])


@router.get("/current")
async def get_current_environment(
    latitude: float = Query(None, description="纬度"),
    longitude: float = Query(None, description="经度"),
    address: str = Query("", description="手动地址"),
    location: str = Query(None, description="位置坐标，格式：经度,纬度")
):
    """
    获取当前环境数据

    支持两种方式：
    1. 提供 latitude 和 longitude
    2. 提供 location，格式为 "经度,纬度"（如 "116.4,39.9"）
    """
    lat = latitude
    lng = longitude

    if location and not (lat and lng):
        try:
            parts = location.split(",")
            if len(parts) == 2:
                lng = float(parts[0])
                lat = float(parts[1])
        except (ValueError, IndexError):
            pass

    env_data = await environment_service.get_environment(
        latitude=lat,
        longitude=lng,
        address=address
    )

    return {
        "latitude": env_data.latitude,
        "longitude": env_data.longitude,
        "address": env_data.address,
        "weather": env_data.weather,
        "temperature": env_data.temperature,
        "humidity": env_data.humidity,
        "wind_speed": env_data.wind_speed,
        "pressure": env_data.pressure,
        "visibility": env_data.visibility,
        "recorded_at": env_data.recorded_at
    }


@router.get("/weather")
async def get_weather(
    location: str = Query(..., description="位置坐标，格式：经度,纬度")
):
    """获取指定位置的天气信息"""
    weather_data = await environment_service.get_current_weather(location)
    return weather_data


@router.post("/manual")
async def submit_manual_environment(
    address: str = Query(..., description="地址"),
    weather: str = Query("", description="天气状况"),
    temperature: float = Query(None, description="温度(℃)"),
    humidity: float = Query(None, description="湿度(%)")
):
    """手动提交环境数据"""
    env_data = await environment_service.get_environment(
        address=address,
        manual_weather={
            "weather": weather,
            "temperature": temperature,
            "humidity": humidity
        }
    )

    return {
        "address": env_data.address,
        "weather": env_data.weather,
        "temperature": env_data.temperature,
        "humidity": env_data.humidity,
        "status": "success"
    }