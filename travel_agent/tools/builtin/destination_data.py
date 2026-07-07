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


class DestinationDataTool(BaseTool):
    name = "destination_data"
    description = "Load local destination spots, restaurants, hotels and map center."

    def run(self, **kwargs: Any) -> dict[str, Any]:
        destination = kwargs.get("destination", "上海")
        if destination in DESTINATIONS:
            return DESTINATIONS[destination]
        fallback = DESTINATIONS["上海"].copy()
        fallback["unknown_destination"] = destination
        return fallback
