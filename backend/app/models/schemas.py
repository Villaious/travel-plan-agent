from __future__ import annotations

from datetime import date
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

from travel_agent.data import normalize_china_destination


BudgetLevel = Literal["经济", "舒适", "品质"]
T = TypeVar("T")


class FlexibleModel(BaseModel):
    class Config:
        extra = "allow"


class ApiResponse(BaseModel, Generic[T]):
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(default="", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")


class TripEditRequest(BaseModel):
    plan: dict[str, Any] = Field(..., description="当前行程计划")
    action: Literal["add", "delete", "move"] = Field(..., description="编辑动作")
    day_index: int = Field(default=0, ge=0, description="第几天，从0开始")
    stop_index: int | None = Field(default=None, description="停靠点索引")
    target_index: int | None = Field(default=None, description="移动目标索引")
    stop: dict[str, Any] | None = Field(default=None, description="新增停靠点")


class ExportRequest(BaseModel):
    plan: dict[str, Any] = Field(..., description="行程计划")


class DestinationGroupModel(BaseModel):
    province: str = Field(..., description="省级地区名称")
    cities: list[str] = Field(default_factory=list, description="该地区允许选择的城市")


class TripPlanRequest(BaseModel):
    destination: str = Field(..., min_length=1, description="目的地城市", examples=["上海市"])

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        return normalize_china_destination(value)
    start_date: date = Field(..., description="出发日期", examples=["2026-08-01"])
    days: int = Field(default=2, ge=1, le=7, description="旅行天数")
    preferences: list[str] = Field(default_factory=list, description="旅行偏好")
    budget_level: BudgetLevel = Field(default="舒适", description="预算档位")
    people: int = Field(default=1, ge=1, le=20, description="出行人数")
    transportation: str = Field(default="公共交通", description="交通方式")
    free_text_input: str = Field(default="", description="额外要求")


class POISearchRequest(BaseModel):
    keywords: str = Field(..., min_length=1, description="搜索关键词")
    city: str = Field(default="上海", description="城市")
    citylimit: bool = Field(default=True, description="是否限制城市范围")
    offset: int = Field(default=10, ge=1, le=25, description="返回数量")


class RouteRequest(BaseModel):
    points: list[dict[str, float | str]] = Field(..., min_length=2, description="路线点位列表")
    route_type: Literal["walking", "driving", "transit", "cycling"] = Field(default="walking", description="路线类型")
    city: str = Field(default="", description="公交路线所在城市")


TravelMode = Literal["transit", "driving", "walking", "cycling"]
RoutePriority = Literal["balanced", "time", "cost"]


class RoutePointModel(BaseModel):
    name: str = Field(..., min_length=1, description="地点名称")
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lng: float = Field(..., ge=-180, le=180, description="经度")


class DistanceMeasureRequest(BaseModel):
    origins: list[RoutePointModel] = Field(..., min_length=1, max_length=100, description="起点列表")
    destination: RoutePointModel = Field(..., description="终点")
    distance_type: Literal[0, 1, 3] = Field(default=0, description="0直线、1驾车、3步行")


class CoordinateConvertRequest(BaseModel):
    locations: list[RoutePointModel] = Field(..., min_length=1, max_length=40, description="待转换坐标")
    coordsys: Literal["gps", "mapbar", "baidu", "autonavi"] = Field(default="gps", description="原坐标系")

class RouteRecommendationRequest(BaseModel):
    city: str = Field(..., min_length=1, description="路线所在城市")
    origin: RoutePointModel = Field(..., description="起点")
    destination: RoutePointModel = Field(..., description="终点")
    selected_modes: list[TravelMode] = Field(..., min_length=1, description="参与比较的交通方式")
    priority: RoutePriority = Field(default="balanced", description="推荐侧重：综合、时间或费用")
    people: int = Field(default=1, ge=1, le=20, description="出行人数")

    @model_validator(mode="after")
    def validate_distinct_points(self):
        if self.origin.lat == self.destination.lat and self.origin.lng == self.destination.lng:
            raise ValueError("起点和终点不能相同")
        return self


class RouteOptionModel(BaseModel):
    mode: TravelMode
    label: str
    distance_km: float
    duration_minutes: int
    estimated_cost: float
    cost_per_person: float
    comfort_score: int
    source: str
    polyline: list[list[float]] = Field(default_factory=list)
    description: str = ""
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    score: float = 0
    recommended: bool = False


class RouteRecommendationModel(BaseModel):
    agent: str
    city: str
    origin: RoutePointModel
    destination: RoutePointModel
    priority: RoutePriority
    recommended_mode: TravelMode
    recommended_label: str
    recommendation: str
    options: list[RouteOptionModel] = Field(default_factory=list)
    message: str = ""
    topic_check: dict[str, Any] = Field(default_factory=dict)


class ErrorDetail(BaseModel):
    code: str = Field(default="ERROR", description="错误代码")
    detail: str = Field(..., description="错误详情")


class LocationModel(FlexibleModel):
    lat: float | None = Field(default=None, description="纬度")
    lng: float | None = Field(default=None, description="经度")


class StopModel(FlexibleModel):
    name: str = Field(..., description="地点名称")
    category: str = Field(default="spot", description="类型：spot/restaurant/hotel")
    time: str = Field(default="", description="安排时间")
    reason: str = Field(default="", description="安排理由")
    lat: float | None = Field(default=None, description="纬度")
    lng: float | None = Field(default=None, description="经度")
    ticket: int = Field(default=0, description="门票费用")
    price: int = Field(default=0, description="餐饮或酒店费用")
    duration: int = Field(default=60, description="建议停留分钟数")


class HotelModel(FlexibleModel):
    name: str = Field(default="待定酒店", description="酒店名称")
    level: str = Field(default="", description="酒店档位")
    price: int = Field(default=0, description="每晚费用")
    lat: float | None = Field(default=None, description="纬度")
    lng: float | None = Field(default=None, description="经度")


class WeatherModel(FlexibleModel):
    date: str = Field(default="", description="日期")
    weather: str = Field(default="", description="天气")
    temperature: int = Field(default=0, description="温度")
    suggestion: str = Field(default="", description="天气建议")
    source: str = Field(default="", description="数据来源")


class DayPlanModel(FlexibleModel):
    day: int = Field(..., description="第几天")
    date: str = Field(..., description="日期")
    hotel: HotelModel = Field(default_factory=HotelModel, description="推荐酒店")
    stops: list[StopModel] = Field(default_factory=list, description="当日停靠点")


class ItineraryModel(FlexibleModel):
    destination: str = Field(..., description="目的地")
    days: list[DayPlanModel] = Field(default_factory=list, description="每日行程")
    preferences: list[str] = Field(default_factory=list, description="旅行偏好")
    transportation: str = Field(default="公共交通", description="交通方式")
    scenic_insights: list[dict[str, Any]] = Field(default_factory=list, description="景区搜索Agent整理结果")
    summary: str = Field(default="", description="行程摘要")
    weather_info: list[WeatherModel] = Field(default_factory=list, description="天气信息")
    overall_suggestions: str = Field(default="", description="总体建议")
    llm_used: bool = Field(default=False, description="是否使用LLM增强")


class BudgetModel(BaseModel):
    ticket: int = Field(default=0, description="门票费用")
    hotel: int = Field(default=0, description="酒店费用")
    food: int = Field(default=0, description="餐饮费用")
    transport: int = Field(default=0, description="交通费用")
    total: int = Field(default=0, description="总费用")
    people: int = Field(default=1, description="人数")
    currency: str = Field(default="CNY", description="币种")


class MarkerModel(FlexibleModel):
    name: str = Field(..., description="标记名称")
    lat: float = Field(..., description="纬度")
    lng: float = Field(..., description="经度")
    day: int = Field(default=1, description="第几天")
    category: str = Field(default="spot", description="标记类型")
    label: str = Field(default="", description="地图标签")


class RouteModel(BaseModel):
    day: int = Field(..., description="第几天")
    points: list[list[float]] = Field(default_factory=list, description="路线点")
    distance_km: float = Field(default=0, description="距离公里")


class MapModel(BaseModel):
    center: list[float] = Field(default_factory=list, description="地图中心点")
    markers: list[MarkerModel] = Field(default_factory=list, description="地图标记")
    routes: list[RouteModel] = Field(default_factory=list, description="路线")


class TopicCheckModel(BaseModel):
    agent: str = Field(..., description="被检查Agent")
    on_topic: bool = Field(..., description="是否围绕原始话题")
    reason: str = Field(default="", description="检查原因")
    travel_keyword_hits: int = Field(default=0, description="旅行关键词命中数")
    off_topic_keywords: list[str] = Field(default_factory=list, description="跑题关键词")


class CollaborationTraceModel(BaseModel):
    step: int = Field(..., description="步骤序号")
    agent: str = Field(..., description="Agent名称")
    input: str = Field(default="", description="该Agent输入")
    output: str = Field(default="", description="该Agent输出")
    status: str = Field(default="ok", description="步骤状态")


class TripPlanResponseModel(BaseModel):
    title: str = Field(..., description="计划标题")
    summary: str = Field(..., description="计划摘要")
    itinerary: ItineraryModel = Field(..., description="行程内容")
    budget: BudgetModel = Field(..., description="预算明细")
    map: MapModel = Field(..., description="地图数据")
    topic_checks: list[TopicCheckModel] = Field(default_factory=list, description="主题检查结果")
    collaboration_trace: list[CollaborationTraceModel] = Field(default_factory=list, description="多Agent协作轨迹")
    memory_suggestions: dict[str, Any] = Field(default_factory=dict, description="历史偏好建议")
    memory_snapshot: dict[str, Any] = Field(default_factory=dict, description="记忆快照")
    transportation: str = Field(default="公共交通", description="交通方式")
    scenic_insights: list[dict[str, Any]] = Field(default_factory=list, description="景区搜索Agent整理结果")


class ConfigStatusModel(BaseModel):
    status: str = Field(default="ok", description="服务状态")
    amap_api_key_configured: bool = Field(..., description="是否配置高德Key")
    amap_js_api_key_configured: bool = Field(default=False, description="是否配置高德Web端JS API Key")
    amap_js_security_code_configured: bool = Field(default=False, description="是否配置高德Web端JS安全密钥")
    amap_js_expose_security: bool = Field(default=False, description="是否允许前端明文读取JS安全密钥")
    llm_api_key_configured: bool = Field(..., description="是否配置LLM Key")
    qdrant_configured: bool = Field(default=False, description="是否配置Qdrant向量数据库")
    serpapi_configured: bool = Field(default=False, description="是否配置SerpApi搜索API")
    travel_agent_use_llm: bool = Field(..., description="是否启用LLM增强")
    amap_mode: str = Field(..., description="高德数据模式：api/local_fallback")
    amap_js_mode: str = Field(default="fallback_svg", description="前端地图模式：js_api/fallback_svg")
    llm_mode: str = Field(..., description="LLM模式：api/rule_fallback/disabled")
    rag_mode: str = Field(default="disabled", description="景点知识库模式：qdrant_rag/disabled")
    scenic_search_mode: str = Field(default="rule_fallback", description="景区搜索模式：serpapi/rule_fallback")
    amap_web_qps_limit: int = Field(default=3, description="高德通用 Web 服务每秒并发上限")
    amap_route_qps_limit: int = Field(default=3, description="高德路线规划每秒并发上限")
    amap_search_qps_limit: int = Field(default=3, description="高德搜索服务每秒并发上限")
    amap_weather_qps_limit: int = Field(default=3, description="高德天气服务每秒并发上限")
    amap_static_map_qps_limit: int = Field(default=3, description="高德静态地图每秒并发上限")
    amap_js_qps_limit: int = Field(default=10, description="高德 JS 地图初始化每秒上限")
    amap_rate_limit_mode: str = Field(default="shared_in_process", description="高德限流模式")
    llm_base_url: str = Field(default="", description="LLM Base URL")
    llm_model: str = Field(default="", description="LLM模型")

class AmapJsConfigModel(BaseModel):
    enabled: bool = Field(..., description="是否启用高德Web端JS地图")
    key: str = Field(default="", description="高德Web端JS API Key")
    security_js_code: str = Field(default="", description="高德Web端JS安全密钥，仅开发模式按需返回")
    expose_security: bool = Field(default=False, description="是否已允许前端明文使用安全密钥")
    service_host: str = Field(default="", description="生产环境代理服务地址")
    qps_limit: int = Field(default=10, description="JS 地图初始化每秒上限")
    message: str = Field(default="", description="配置说明")

TripPlanData = TripPlanResponseModel







