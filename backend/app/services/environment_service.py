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
    province: str = ""
    city: str = ""
    district: str = ""
    county: str = ""
    township: str = ""
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
        self.is_amap = "restapi.amap.com" in (self.base_url or "")

    async def get_current_weather(self, location: str) -> Dict[str, Any]:
        """获取实时天气"""
        if not self.api_key:
            return {"error": "天气API未配置"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if self.is_amap:
                    weather_url = self.base_url.rstrip('/')
                    if "weatherInfo" not in weather_url:
                        weather_url = f"{weather_url}/v3/weather/weatherInfo"
                    response = await client.get(
                        weather_url,
                        params={
                            "key": self.api_key,
                            "city": location,
                            "extensions": "base",
                        }
                    )
                else:
                    response = await client.get(
                        f"{self.base_url.rstrip('/')}/v7/weather/now",
                        params={
                            "key": self.api_key,
                            "location": location
                        }
                    )
                response.raise_for_status()
                data = response.json()

                if self.is_amap and data.get("status") == "1":
                    live_list = data.get("lives", []) or []
                    live = live_list[0] if live_list else {}
                    return {
                        "temperature": float(live.get("temperature_float") or live.get("temperature") or 0),
                        "feels_like": float(live.get("temperature_float") or live.get("temperature") or 0),
                        "humidity": float(live.get("humidity_float") or live.get("humidity") or 0),
                        "wind_speed": live.get("windpower"),
                        "wind_dir": live.get("winddirection", ""),
                        "pressure": None,
                        "visibility": None,
                        "weather": live.get("weather", ""),
                        "weather_code": "",
                        "recorded_at": live.get("reporttime", "")
                    }
                if (not self.is_amap) and data.get("code") == "200":
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
                err_code = data.get("code") or data.get("infocode") or data.get("status")
                return {"error": f"API错误: {err_code}"}
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
        details = await self.reverse_geocode_details(latitude, longitude)
        return details.get("address", f"{latitude},{longitude}")

    async def reverse_geocode_details(self, latitude: float, longitude: float) -> Dict[str, str]:
        """将经纬度转换为结构化地址"""
        if not self.api_key:
            fallback = f"{latitude},{longitude}"
            return {
                "address": fallback,
                "province": "",
                "city": "",
                "district": "",
                "county": "",
                "township": "",
                "adcode": "",
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/v3/geocode/regeo",
                    params={
                        "key": self.api_key,
                        "location": f"{longitude},{latitude}",
                        "extensions": "all"
                    }
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "1":
                    regeocode = data.get("regeocode", {})
                    component = regeocode.get("addressComponent", {}) or {}
                    district = component.get("district", "") or ""
                    county = district
                    city = component.get("city", "")
                    if isinstance(city, list):
                        city = city[0] if city else ""
                    if not city:
                        city = component.get("province", "") or ""
                    return {
                        "address": regeocode.get("formatted_address", "") or f"{latitude},{longitude}",
                        "province": component.get("province", "") or "",
                        "city": city or "",
                        "district": district,
                        "county": county,
                        "township": component.get("township", "") or "",
                        "adcode": component.get("adcode", "") or "",
                    }
                fallback = f"{latitude},{longitude}"
                return {
                    "address": fallback,
                    "province": "",
                    "city": "",
                    "district": "",
                    "county": "",
                    "township": "",
                    "adcode": "",
                }
        except Exception:
            fallback = f"{latitude},{longitude}"
            return {
                "address": fallback,
                "province": "",
                "city": "",
                "district": "",
                "county": "",
                "township": "",
                "adcode": "",
            }

    async def get_weather_by_coordinates(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """通过坐标获取天气"""
        weather_service = WeatherService()
        location = f"{longitude},{latitude}"
        return await weather_service.get_current_weather(location)

    async def ip_location(self, client_ip: str = "") -> Dict[str, Any]:
        """通过IP定位（高德IP定位）"""
        if not self.api_key:
            return {"address": "", "province": "", "city": "", "district": "", "county": "", "township": ""}

        try:
            params = {"key": self.api_key}
            ip_value = (client_ip or "").strip()
            if ip_value and ip_value not in {"127.0.0.1", "::1", "localhost"}:
                params["ip"] = ip_value

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/v3/ip", params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "1":
                return {"address": "", "province": "", "city": "", "district": "", "county": "", "township": ""}

            province = data.get("province", "") or ""
            city = data.get("city", "") or ""
            district = data.get("district", "") or ""
            if isinstance(province, list):
                province = province[0] if province else ""
            if isinstance(city, list):
                city = city[0] if city else ""
            if isinstance(district, list):
                district = district[0] if district else ""
            county = district
            address = "".join([province, city, district]).strip()
            return {
                "address": address,
                "province": province,
                "city": city,
                "district": district,
                "county": county,
                "township": "",
                "adcode": (data.get("adcode")[0] if isinstance(data.get("adcode"), list) and data.get("adcode") else data.get("adcode", "")) or "",
            }
        except Exception:
            return {"address": "", "province": "", "city": "", "district": "", "county": "", "township": "", "adcode": ""}


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
        address_details = {
            "province": "",
            "city": "",
            "district": "",
            "county": "",
            "township": "",
        }

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            if not result:
                continue

            if i == 0 and isinstance(result, dict):
                resolved_address = result.get("address", "") or resolved_address
                address_details = result
            elif i == 1 and isinstance(result, dict):
                weather_data = result
            elif i == 2 and isinstance(result, dict):
                weather_data = result

        return EnvironmentData(
            latitude=latitude,
            longitude=longitude,
            address=resolved_address,
            province=address_details.get("province", ""),
            city=address_details.get("city", ""),
            district=address_details.get("district", ""),
            county=address_details.get("county", ""),
            township=address_details.get("township", ""),
            weather=weather_data.get("weather", ""),
            temperature=weather_data.get("temperature"),
            humidity=weather_data.get("humidity"),
            wind_speed=weather_data.get("wind_speed"),
            pressure=weather_data.get("pressure"),
            visibility=weather_data.get("visibility"),
            recorded_at=weather_data.get("recorded_at") or datetime.now().isoformat()
        )

    async def _get_address_from_coords(self, latitude: float, longitude: float) -> Dict[str, str]:
        """通过坐标获取地址"""
        map_service = MapService()
        return await map_service.reverse_geocode_details(latitude, longitude)

    async def _get_weather_from_coords(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """通过坐标获取天气"""
        weather_service = WeatherService()
        if weather_service.is_amap:
            map_service = MapService()
            detail = await map_service.reverse_geocode_details(latitude, longitude)
            city_code = detail.get("adcode") or detail.get("city") or detail.get("province")
            if not city_code:
                return {}
            weather = await weather_service.get_current_weather(city_code)
            if weather.get("error"):
                return {}
            return weather

        location = f"{longitude},{latitude}"
        return await weather_service.get_current_weather(location)

    async def get_current_weather(self, location: str) -> Dict[str, Any]:
        """获取指定位置的天气"""
        weather_service = WeatherService()
        return await weather_service.get_current_weather(location)

    async def get_environment_by_ip(self, client_ip: str = "") -> EnvironmentData:
        """通过IP定位获取基础环境（不依赖前端定位权限）"""
        map_service = MapService()
        ip_data = await map_service.ip_location(client_ip)
        address = ip_data.get("address", "") or ""
        city = ip_data.get("adcode") or ip_data.get("city", "") or ""
        if not address:
            address = "".join([ip_data.get("province", "") or "", ip_data.get("city", "") or "", ip_data.get("district", "") or ""]).strip()
        if not address:
            address = "本地网络未提供IP归属地，请开启浏览器定位"
        weather_data = {}
        if city:
            weather_data = await WeatherService().get_current_weather(city)
            if weather_data.get("error"):
                weather_data = {}

        return EnvironmentData(
            address=address,
            province=ip_data.get("province", "") or "",
            city=city,
            district=ip_data.get("district", "") or "",
            county=ip_data.get("county", "") or "",
            township=ip_data.get("township", "") or "",
            weather=weather_data.get("weather", ""),
            temperature=weather_data.get("temperature"),
            humidity=weather_data.get("humidity"),
            wind_speed=weather_data.get("wind_speed"),
            pressure=weather_data.get("pressure"),
            visibility=weather_data.get("visibility"),
            recorded_at=weather_data.get("recorded_at") or datetime.now().isoformat()
        )


environment_service = EnvironmentService()
