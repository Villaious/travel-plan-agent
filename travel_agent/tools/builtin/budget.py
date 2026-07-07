from typing import Any

from travel_agent.tools.base import BaseTool


class BudgetTool(BaseTool):
    name = "budget"
    description = "Calculate ticket, hotel, food and transport costs."

    def run(self, **kwargs: Any) -> dict[str, Any]:
        itinerary = kwargs["itinerary"]
        people = max(1, int(kwargs.get("people", 1)))
        transport_per_day = int(kwargs.get("transport_per_day", 80))

        ticket = 0
        food = 0
        for day in itinerary["days"]:
            for stop in day["stops"]:
                ticket += int(stop.get("ticket", 0)) * people
                if stop.get("category") == "restaurant":
                    food += int(stop.get("price", 80)) * people

        nights = max(1, len(itinerary["days"]) - 1)
        hotel = sum(int(day["hotel"]["price"]) for day in itinerary["days"][:nights])
        transport = transport_per_day * len(itinerary["days"]) * people
        total = ticket + food + hotel + transport

        return {
            "ticket": ticket,
            "hotel": hotel,
            "food": food,
            "transport": transport,
            "total": total,
            "people": people,
            "currency": "CNY",
        }
