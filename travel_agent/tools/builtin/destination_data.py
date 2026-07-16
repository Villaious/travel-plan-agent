from typing import Any

from travel_agent.tools.base import BaseTool


DESTINATIONS: dict[str, dict[str, Any]] = {
    "上海": {
        "center": [31.2304, 121.4737],
        "spots": [
            {"name": "外滩", "type": "城市漫步", "lat": 31.2400, "lng": 121.4900, "ticket": 0, "duration": 90, "tags": ["城市漫步", "摄影", "夜景"], "reason": "经典城市天际线，适合作为上海第一站。"},
            {"name": "豫园", "type": "文化", "lat": 31.2272, "lng": 121.4921, "ticket": 40, "duration": 100, "tags": ["文化", "园林", "历史"], "reason": "江南园林和老城厢风貌集中，文化密度高。"},
            {"name": "上海博物馆", "type": "文化", "lat": 31.2304, "lng": 121.4700, "ticket": 0, "duration": 120, "tags": ["文化", "博物馆", "雨天"], "reason": "适合系统了解城市与中国艺术收藏。"},
            {"name": "田子坊", "type": "美食", "lat": 31.2107, "lng": 121.4692, "ticket": 0, "duration": 90, "tags": ["美食", "文创", "城市漫步"], "reason": "小巷、咖啡和本地小吃适合轻松穿插。"},
            {"name": "上海迪士尼度假区", "type": "亲子", "lat": 31.1440, "lng": 121.6570, "ticket": 475, "duration": 480, "tags": ["亲子", "主题乐园"], "reason": "适合亲子和娱乐偏好，但会占用完整一天。"},
            {"name": "武康路", "type": "城市漫步", "lat": 31.2145, "lng": 121.4435, "ticket": 0, "duration": 100, "tags": ["城市漫步", "摄影", "咖啡"], "reason": "街区尺度友好，适合下午慢逛。"},
        ],
        "restaurants": [
            {"name": "绿波廊", "lat": 31.2270, "lng": 121.4916, "price": 120, "tags": ["本帮菜", "文化"]},
            {"name": "佳家汤包", "lat": 31.2395, "lng": 121.4803, "price": 45, "tags": ["小吃", "美食"]},
            {"name": "衡山小馆", "lat": 31.2058, "lng": 121.4490, "price": 95, "tags": ["本帮菜", "城市漫步"]},
        ],
        "hotels": [
            {"name": "人民广场精选酒店", "lat": 31.2324, "lng": 121.4707, "price": 520, "level": "舒适"},
            {"name": "南京东路轻居酒店", "lat": 31.2387, "lng": 121.4828, "price": 360, "level": "经济"},
            {"name": "外滩景观酒店", "lat": 31.2415, "lng": 121.4942, "price": 980, "level": "品质"},
        ],
    },
    "北京": {
        "center": [39.9042, 116.4074],
        "spots": [
            {"name": "故宫博物院", "type": "文化", "lat": 39.9163, "lng": 116.3972, "ticket": 60, "duration": 240, "tags": ["文化", "历史", "博物馆"], "reason": "北京文化旅行的核心地标。"},
            {"name": "景山公园", "type": "城市漫步", "lat": 39.9250, "lng": 116.3965, "ticket": 2, "duration": 60, "tags": ["摄影", "城市漫步"], "reason": "俯瞰中轴线，适合接在故宫之后。"},
            {"name": "天坛公园", "type": "文化", "lat": 39.8822, "lng": 116.4066, "ticket": 34, "duration": 150, "tags": ["文化", "建筑", "历史"], "reason": "礼制建筑完整，动线清晰。"},
            {"name": "南锣鼓巷", "type": "美食", "lat": 39.9370, "lng": 116.4033, "ticket": 0, "duration": 90, "tags": ["美食", "胡同", "城市漫步"], "reason": "适合安排晚间小吃和胡同散步。"},
            {"name": "颐和园", "type": "自然", "lat": 39.9999, "lng": 116.2755, "ticket": 30, "duration": 180, "tags": ["自然", "园林", "文化"], "reason": "湖景与皇家园林结合，节奏舒展。"},
        ],
        "restaurants": [
            {"name": "四季民福烤鸭店", "lat": 39.9148, "lng": 116.3970, "price": 160, "tags": ["烤鸭", "文化"]},
            {"name": "姚记炒肝", "lat": 39.9395, "lng": 116.4012, "price": 40, "tags": ["小吃", "美食"]},
            {"name": "护国寺小吃", "lat": 39.9339, "lng": 116.3735, "price": 45, "tags": ["小吃", "美食"]},
        ],
        "hotels": [
            {"name": "前门舒适酒店", "lat": 39.8996, "lng": 116.3976, "price": 480, "level": "舒适"},
            {"name": "鼓楼轻居酒店", "lat": 39.9412, "lng": 116.3961, "price": 330, "level": "经济"},
            {"name": "王府井品质酒店", "lat": 39.9141, "lng": 116.4116, "price": 900, "level": "品质"},
        ],
    },
}

CHINA_REGION_CENTERS: dict[str, list[float]] = {
    "北京": [39.9042, 116.4074], "天津": [39.0842, 117.2009], "上海": [31.2304, 121.4737], "重庆": [29.5630, 106.5516],
    "河北": [38.0428, 114.5149], "石家庄": [38.0428, 114.5149], "山西": [37.8706, 112.5489], "太原": [37.8706, 112.5489],
    "内蒙古": [40.8426, 111.7492], "呼和浩特": [40.8426, 111.7492], "辽宁": [41.8057, 123.4315], "沈阳": [41.8057, 123.4315],
    "吉林": [43.8171, 125.3235], "长春": [43.8171, 125.3235], "黑龙江": [45.8038, 126.5349], "哈尔滨": [45.8038, 126.5349],
    "江苏": [32.0603, 118.7969], "南京": [32.0603, 118.7969], "浙江": [30.2741, 120.1551], "杭州": [30.2741, 120.1551],
    "安徽": [31.8206, 117.2272], "合肥": [31.8206, 117.2272], "福建": [26.0745, 119.2965], "福州": [26.0745, 119.2965],
    "江西": [28.6820, 115.8579], "南昌": [28.6820, 115.8579], "山东": [36.6512, 117.1201], "济南": [36.6512, 117.1201],
    "河南": [34.7466, 113.6254], "郑州": [34.7466, 113.6254], "湖北": [30.5928, 114.3055], "武汉": [30.5928, 114.3055],
    "湖南": [28.2282, 112.9388], "长沙": [28.2282, 112.9388], "广东": [23.1291, 113.2644], "广州": [23.1291, 113.2644],
    "广西": [22.8170, 108.3669], "南宁": [22.8170, 108.3669], "海南": [20.0440, 110.1999], "海口": [20.0440, 110.1999],
    "四川": [30.5728, 104.0668], "成都": [30.5728, 104.0668], "贵州": [26.6470, 106.6302], "贵阳": [26.6470, 106.6302],
    "云南": [25.0389, 102.7183], "昆明": [25.0389, 102.7183], "西藏": [29.6520, 91.1721], "拉萨": [29.6520, 91.1721],
    "陕西": [34.3416, 108.9398], "西安": [34.3416, 108.9398], "甘肃": [36.0611, 103.8343], "兰州": [36.0611, 103.8343],
    "青海": [36.6171, 101.7782], "西宁": [36.6171, 101.7782], "宁夏": [38.4872, 106.2309], "银川": [38.4872, 106.2309],
    "新疆": [43.8256, 87.6168], "乌鲁木齐": [43.8256, 87.6168], "香港": [22.3193, 114.1694], "澳门": [22.1987, 113.5439],
    "台湾": [25.0330, 121.5654], "台北": [25.0330, 121.5654], "深圳": [22.5431, 114.0579], "苏州": [31.2989, 120.5853],
    "厦门": [24.4798, 118.0894], "三亚": [18.2528, 109.5119], "青岛": [36.0671, 120.3826], "大连": [38.9140, 121.6147],
}


class DestinationDataTool(BaseTool):
    name = "destination_data"
    description = "Load local destination spots, restaurants, hotels and map center."

    def run(self, **kwargs: Any) -> dict[str, Any]:
        destination = str(kwargs.get("destination", "上海")).strip() or "上海"
        normalized = self._normalize_destination(destination)
        if normalized in DESTINATIONS:
            return DESTINATIONS[normalized]
        return self._generic_destination(destination, self._center_for(normalized))

    def _normalize_destination(self, destination: str) -> str:
        for suffix in ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "省", "市"):
            if destination.endswith(suffix):
                return destination[: -len(suffix)]
        return destination

    def _center_for(self, destination: str) -> list[float]:
        return CHINA_REGION_CENTERS.get(destination, [35.8617, 104.1954])

    def _generic_destination(self, destination: str, center: list[float]) -> dict[str, Any]:
        lat, lng = center
        return {
            "center": center,
            "spots": [
                self._fallback_place(destination, "城市代表景区", lat + 0.012, lng + 0.008, "城市漫步", ["城市漫步", "摄影"]),
                self._fallback_place(destination, "历史文化场馆", lat - 0.006, lng + 0.014, "文化", ["文化", "历史"]),
                self._fallback_place(destination, "城市公园", lat + 0.004, lng - 0.015, "自然", ["自然", "公园"]),
                self._fallback_place(destination, "特色街区", lat - 0.014, lng - 0.006, "美食", ["美食", "城市漫步"]),
            ],
            "restaurants": [
                {"name": f"{destination}地方菜餐厅（待在线检索）", "lat": lat + 0.003, "lng": lng + 0.004, "price": 90, "tags": ["美食", "地方菜"], "source": "local_fallback"},
                {"name": f"{destination}特色小吃（待在线检索）", "lat": lat - 0.004, "lng": lng - 0.003, "price": 45, "tags": ["美食", "小吃"], "source": "local_fallback"},
            ],
            "hotels": [
                {"name": f"{destination}市中心酒店（待在线检索）", "lat": lat, "lng": lng, "price": 520, "level": "舒适", "source": "local_fallback"},
                {"name": f"{destination}经济酒店（待在线检索）", "lat": lat + 0.006, "lng": lng - 0.005, "price": 320, "level": "经济", "source": "local_fallback"},
                {"name": f"{destination}品质酒店（待在线检索）", "lat": lat - 0.005, "lng": lng + 0.006, "price": 900, "level": "品质", "source": "local_fallback"},
            ],
            "unknown_destination": destination,
        }

    def _fallback_place(self, destination: str, label: str, lat: float, lng: float, place_type: str, tags: list[str]) -> dict[str, Any]:
        return {
            "name": f"{destination}{label}（待在线检索）",
            "type": place_type,
            "lat": lat,
            "lng": lng,
            "ticket": 0,
            "duration": 90,
            "tags": tags,
            "reason": "高德服务不可用时生成的地区级回退点位，请联网后核实具体地点。",
            "source": "local_fallback",
        }
