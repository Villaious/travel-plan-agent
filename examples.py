from travel_agent import TravelPlannerAgent


if __name__ == "__main__":
    agent = TravelPlannerAgent()
    plan = agent.run(
        destination="上海",
        start_date="2026-08-01",
        days=2,
        preferences=["文化", "美食", "城市漫步"],
        budget_level="舒适",
    )

    print(plan["summary"])
    print(f"预算合计: RMB {plan['budget']['total']}")
    print("\n多Agent协作轨迹:")
    for item in plan["collaboration_trace"]:
        print(f"{item['step']}. {item['agent']}: {item['output']}")

    print("\n主题检查:")
    for item in plan["topic_checks"]:
        status = "通过" if item["on_topic"] else "拦截"
        print(f"- {item['agent']}: {status}，{item['reason']}")

    for day in plan["itinerary"]["days"]:
        print(f"\n第 {day['day']} 天 {day['date']}")
        for stop in day["stops"]:
            print(f"- {stop['time']} {stop['name']}：{stop['reason']}")
