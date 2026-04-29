import httpx
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class EnvironmentData:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str = ""
    weather: str = ""
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    pressure: Optional[float] = None
    visibility: Optional[float] = None
    recorded_at: str = ""


class WeatherService:
    """天气数据服务"""

    def __init__(self):
        self.api_key = settings.weather_api_key
        self.base_url = settings.weather_api_base_url

    async def get_current_weather(self, location: str) -> Dict[str, Any]:
        """获取实时天气"""
        if not self.api_key:
            return {"error": "天气API未配置"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/v7/weather/now",
                    params={
                        "key": self.api_key,
                        "location": location
                    }
                )
                response.raise_for_status()
                data = response.json()

                if data.get("code") == "200":
                    now = data.get("now", {})
                    return {
                        "temperature": float(now.get("temp", 0)),
                        "feels_like": float(now.get("feelsLike", 0)),
                        "humidity": float(now.get("humidity", 0)),
                        "wind_speed": float(now.get("windSpeed", 0)),
                        "wind_dir": now.get("windDir", ""),
                        "pressure": float(now.get("pressure", 0)),
                        "visibility": float(now.get("vis", 0)),
                        "weather": now.get("text", ""),
                        "weather_code": now.get("icon", ""),
                        "recorded_at": data.get("updateTime", "")
                    }
                else:
                    return {"error": f"API错误: {data.get('code')}"}
        except httpx.TimeoutException:
            return {"error": "天气请求超时"}
        except Exception as e:
            return {"error": str(e)}


class MapService:
    """地图服务 - 逆地理编码"""

    def __init__(self):
        self.api_key = settings.map_api_key
        self.base_url = settings.map_api_base_url

    async def reverse_geocode(self, latitude: float, longitude: float) -> str:
        """将经纬度转换为地址"""
        if not self.api_key:
            return f"{latitude},{longitude}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/v3/geocode/regeo",
                    params={
                        "key": self.api_key,
                        "location": f"{longitude},{latitude}",
                        "extensions": "base"
                    }
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "1":
                    regeocode = data.get("regeocode", {})
                    address = regeocode.get("formatted_address", "")
                    return address
                else:
                    return f"{latitude},{longitude}"
        except Exception:
            return f"{latitude},{longitude}"

    async def get_weather_by_coordinates(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """通过坐标获取天气"""
        weather_service = WeatherService()
        location = f"{longitude},{latitude}"
        return await weather_service.get_current_weather(location)


class EnvironmentService:
    """环境数据服务 - 并行获取地址和天气"""

    async def get_environment(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: str = "",
        manual_weather: Dict[str, Any] = None
    ) -> EnvironmentData:
        """
        获取环境数据

        Args:
            latitude: 纬度
            longitude: 经度
            address: 手动提供的地址
            manual_weather: 手动提供的天气数据

        Returns:
            EnvironmentData对象
        """
        tasks = []

        if latitude is not None and longitude is not None:
            tasks.append(self._get_address_from_coords(latitude, longitude))
            tasks.append(self._get_weather_from_coords(latitude, longitude))
        else:
            tasks.append(asyncio.sleep(0, result=""))

        if manual_weather:
            tasks.append(asyncio.sleep(0, result=manual_weather))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        resolved_address = address
        weather_data = {}

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            if not result:
                continue

            if i == 0 and isinstance(result, str) and result:
                resolved_address = result
            elif i == 1 and isinstance(result, dict):
                weather_data = result
            elif i == 2 and isinstance(result, dict):
                weather_data = result

        return EnvironmentData(
            latitude=latitude,
            longitude=longitude,
            address=resolved_address,
            weather=weather_data.get("weather", ""),
            temperature=weather_data.get("temperature"),
            humidity=weather_data.get("humidity"),
            wind_speed=weather_data.get("wind_speed"),
            pressure=weather_data.get("pressure"),
            visibility=weather_data.get("visibility"),
            recorded_at=weather_data.get("recorded_at") or datetime.now().isoformat()
        )

    async def _get_address_from_coords(self, latitude: float, longitude: float) -> str:
        """通过坐标获取地址"""
        map_service = MapService()
        return await map_service.reverse_geocode(latitude, longitude)

    async def _get_weather_from_coords(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """通过坐标获取天气"""
        weather_service = WeatherService()
        location = f"{longitude},{latitude}"
        return await weather_service.get_current_weather(location)

    async def get_current_weather(self, location: str) -> Dict[str, Any]:
        """获取指定位置的天气"""
        weather_service = WeatherService()
        return await weather_service.get_current_weather(location)


environment_service = EnvironmentService()
