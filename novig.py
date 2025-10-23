import asyncio
from collections import defaultdict
from dataclasses import asdict
import aiohttp
from .models import FilterList, LiquidityData, GameDetails, Player, Orders
from .novig_api import NovigAPI


class Novig:
    def __init__(self, filters, filter_amount_dict):
        self.filters = FilterList(filter_data=filters)
        self._novig_api = NovigAPI()
        self.filter_dict = filter_amount_dict

    def get_league_ids(self, league_info):
        """Get all the league IDs for a given league that are scheduled within the next 24 hours."""
        return [
            league_id
            for league in (league_info.get("data", {}).get("event", []))
            # if (scheduled := league.get("game", {}).get("scheduled_start")) and self.compare_dates(scheduled) ## Uncommented after testing
            if (league_id := league.get("id"))
        ]


    async def fetch_data(self, session, league):
        """Fetch data for a specific league and filter it based on the league's events."""
        league_ids = self.get_league_ids(await self._novig_api.query_caller(session, "league", league=league))

        tasks = [self.fetch_and_filter(session, event_id, league) for event_id in league_ids]
        results = await asyncio.gather(*tasks)
        flat_results = [market for sublist in results for market in sublist]
        return league, flat_results

    async def fetch_and_filter(self, session, event_id, league):
        """Fetch market data for a specific event and filter it based on the league."""
        market_data = await self._novig_api.query_caller(session, "market", event_id=event_id)
        market_data = self._extract_data(market_data, league)
        filtered_data = self._group_filter(market_data)
        return self._conditional_filter(filtered_data)

    def _group_filter(self, market_data):
        result = defaultdict(lambda: {"liquidity": {}, "additional_data": None})

        for entry in market_data:
            market_description = entry.key_name
            side = entry.liquidity_data.highest_order["side"]

            result[market_description]["liquidity"][side] = asdict(entry.liquidity_data)

            if entry.stat_type == "Team Total":
                split_name = entry.key_name.rsplit(" ", 2)[0]
                bet_info = f"{entry.bet_info} {split_name}"
            else:
                bet_info = entry.bet_info if not entry.player_name else None

            result[market_description]["additional_data"] = {
                "player_name": entry.player_name,
                "stat_type": entry.stat_type,
                "line": entry.line,
                "game_title": entry.game_details.game_title,
                "game_start_time": entry.game_details.game_start_time,
                "type": "player" if entry.player_name else "Game",
                "bet_info": bet_info
            }

        return [
            {
                "key_name": market,
                "liquidity": data["liquidity"],
                "additional_data": data["additional_data"],
            }
            for market, data in result.items()
        ]

    @staticmethod
    def price_to_american(price: float) -> int:
        if price >= 1 or price <= 0:
            raise ValueError("Price must be between 0 and 1 (exclusive).")

        if price >= 0.5:
            odds = - (price / (1 - price)) * 100
        else:
            odds = ((1 - price) / price) * 100

        return int(round(odds))

    def _conditional_filter(self, market_data: list) -> list:
        """Apply the configured filter to market_data based on filter_dict."""

        filters = {
            "total_and_difference": self._difference_and_total_filter,
            "total_difference": self._total_difference,
        }

        filter_type = self.filter_dict.get("filter_type")
        if filter_type not in filters:
            raise ValueError(
                f"Invalid filter_type: {filter_type}. "
                f"Options are: {', '.join(filters.keys())}"
            )

        if filter_type == "total_and_difference":
            diff = self.filter_dict.get("difference_amount")
            highest = self.filter_dict.get("highest_order_amount")

            if diff is None or highest is None:
                raise ValueError(
                    "'difference_amount' and 'highest_order_amount' must be provided "
                    "for 'total_and_difference'."
                )
            return filters[filter_type](diff, highest, market_data)

        if filter_type == "total_difference":
            diff = self.filter_dict.get("difference_amount")
            if diff is None:
                raise ValueError("'difference_amount' must be provided for 'total_difference'.")
            return filters[filter_type](diff, market_data)

        return market_data

    def _total_difference(self, difference_amount, market_data):
       # Filter markets where the difference between over and under liquidity meets or exceeds the specified amount
        results = []

        for data in market_data:
            liquidity = data.get("liquidity", {})

            if "over" in liquidity and "under" in liquidity:
                over_liquidity_amount = (
                    liquidity.get("over", {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )
                under_liquidity_amount = (
                    liquidity.get("under", {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )
            else:
                sides = list(liquidity.keys())
                if len(sides) < 2:
                    continue

                over_liquidity_amount = (
                    liquidity.get(sides[0], {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )
                under_liquidity_amount = (
                    liquidity.get(sides[1], {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )

            liqudity_difference = round(abs(over_liquidity_amount - under_liquidity_amount), 2)

            if liqudity_difference >= difference_amount:
                data["liqudity_difference"] = liqudity_difference
                results.append(data)

        return results

    def _difference_and_total_filter(self, difference_amount, highest_order_amount, market_data):
        # Filter markets where the difference between over and under liquidity meets or exceeds the specified amount
        results = []

        for data in market_data:
            liquidity = data.get("liquidity", {})

            if "over" in liquidity and "under" in liquidity:
                over_liquidity_amount = (
                    liquidity.get("over", {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )
                under_liquidity_amount = (
                    liquidity.get("under", {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )
            else:
                sides = list(liquidity.keys())
                if len(sides) < 2:
                    continue

                over_liquidity_amount = (
                    liquidity.get(sides[0], {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )
                under_liquidity_amount = (
                    liquidity.get(sides[1], {})
                    .get("highest_order", {})
                    .get("total_liquidity", 0)
                )


            liqudity_difference = round(abs(over_liquidity_amount - under_liquidity_amount), 2)

            over_highest_amount = data.get("liquidity", {}).get("over", {}).get("highest_order")
            under_highest_amount = data.get("liquidity", {}).get("under", {}).get("highest_order")

            if liqudity_difference >= difference_amount and (
                    ((over_highest_amount or {}).get("liquidity_left", 0) >= highest_order_amount)
                    or
                    ((under_highest_amount or {}).get("liquidity_left", 0) >= highest_order_amount)
            ):
                data["liqudity_difference"] = liqudity_difference
                results.append(data)

        return results

    def _map_data(self, market_name: str, league: str) -> dict:
        for stat in self.filters.filter_data.get(league, []):
            if stat.raw_name and stat.raw_name.lower() == market_name.lower():
                return {
                    "valid": bool(stat.active),
                    "stat_type": stat.display_name,
                } if stat.active else {"valid": False, "stat_type": market_name}

        return {"valid": False, "stat_type": market_name}

    def _get_line(self, description):
        keywords = {"over", "under"}  # set is faster for membership checks
        split = next((word for word in description.lower().split() if word not in keywords), None)
        return split

    @staticmethod
    def calculate_liquidity(qty, price):
        return (1-price) * (qty / 100)

    def _get_highest_order(self, orders, direction_description, link_id, stat_type):
        if not orders:
            return None

        highest = max(orders, key=lambda o: o["qty"] * o["price"])
        total_liquidity = sum(self.calculate_liquidity(order.get("qty"), order.get("price")) for order in orders)
        total_qty = sum(order.get("qty", 0) for order in orders)
        weighted_avg_price = sum(
            order.get("price", 0) * order.get("qty", 0) for order in orders
        ) / total_qty

        if stat_type == "Moneyline" or stat_type == "Spread":
            side = direction_description
        else:
            side = "over" if "over" in direction_description.lower() else "under"

        return {
            "total_win": round(highest["qty"] / 100, 2),
            "total_risk": round(highest["price"] * (highest["qty"] / 100), 2),
            "liquidity_left": round(self.calculate_liquidity(highest["qty"], highest["price"]), 2),
            "american_price": self.price_to_american(highest["price"]),
            "total_liquidity": round(total_liquidity, 2),
            "cost_avg_odds": round(self.price_to_american(weighted_avg_price), 2),
            "side": side,
            "outcome_id": link_id,
            # "mobile_link": f"https://novig.onelink.me/JHQQ/events/{link_id}",
            "mobile_link": f"novigapp://events/{link_id}",
            "desktop_link": f"https://app.novig.us/events/{link_id}"
        }

    def _extract_data(self, market_data, league):
        market_data_list = []

        for event in market_data.get("data").get("event", []):
            for market in event.get("markets", []):
                if len(market.get("outcomes", [])) <= 0:
                    continue

                key_market_description = market.get("description", "")
                market_name = market.get("type")

                market_data_list.extend([
                    Player(
                        player_name=market.get("player", {}).get("full_name") if market.get("player") else None,
                        stat_type=self._map_data(market_name, league).get("stat_type"),
                        bet_info=outcome.get("description").title() if outcome.get("description") else None,
                        line=market.get("strike") if market.get("strike") != 0 else None,
                        key_name=key_market_description,
                        orders=[
                            Orders(
                                outcome_id=outcome.get("id"),
                                qty=order.get("qty"),
                                decimal_price=order.get("price"),
                                original_qty=order.get("originalQty"),
                                created_at=order.get("created_at"),
                                american_price=self.price_to_american(order.get("price")),
                                total_win=round(order.get("qty") / 100,2),
                                total_risk=round(order.get("price") * (order.get("qty") / 100), 2),
                                liquidity_left=round(self.calculate_liquidity(order.get("qty"), order.get("price")), 2)
                            )

                            for order in outcome.get("orders", [])
                            if order.get("status") == "OPEN"
                        ],
                        liquidity_data=LiquidityData(
                            highest_order=self._get_highest_order(outcome.get("orders", []), outcome.get("description"), outcome.get("id"), self._map_data(market_name, league).get("stat_type"),)
                        ),
                        game_details=GameDetails(
                            game_title=event.get("description"),
                            game_start_time=event.get("game", {}).get("scheduled_start")
                        )
                    )
                    for outcome in market.get("outcomes", [])
                    if any(order.get("status") == "OPEN" for order in outcome.get("orders", [])) and self._map_data(market_name, league).get("valid")
                ])
        return market_data_list


    async def run(self):
        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(
                *(self.fetch_data(session, league) for league in self.filters.get_leagues())
            )

            return dict(results)

    @classmethod
    async def get_raw_data(cls, leagues: list):
        """Fetch raw market data for all leagues without filtering, grouped by league."""
        api = NovigAPI()

        async with aiohttp.ClientSession() as session:
            # Fetch league-level data
            league_responses = await asyncio.gather(
                *(api.query_caller(session, "league", league=league) for league in leagues)
            )

            league_data = {league: resp for league, resp in zip(leagues, league_responses)}

            # For each league, fetch markets for all event IDs
            results = {}
            for league, resp in league_data.items():
                event_ids = [
                    event.get("id")
                    for event in resp.get("data", {}).get("event", [])
                    if event.get("id")
                ]

                if not event_ids:
                    results[league] = []
                    continue

                market_responses = await asyncio.gather(
                    *(api.query_caller(session, "market", event_id) for event_id in event_ids)
                )
                results[league] = market_responses

            return results

#
if __name__ == "__main__":
    # Load filters from file
    import json
    with open("filters.json", "r") as f:
        filters = json.load(f)

    # # Choose your filter type and amounts
    # total_and_difference_filter = {
    #     # "filter_type": "total_difference",
    #     "filter_type": "total_and_difference",
    #     "difference_amount": 0,
    #     "highest_order_amount": 0
    # }

    # OR

    total_difference_filter = {
        "filter_type": "total_difference",
        "difference_amount": 0,
    }

    # Create Novig instance
    novig = Novig(filters=filters, filter_amount_dict=total_difference_filter)

    # Run it
    results = asyncio.run(novig.run())
    with open("results.json", "w") as f:
        json.dump(results, f, indent=4)

# if __name__ == "__main__":
#     raw = asyncio.run(Novig.get_raw_data(["NFL"]))
#     import json
#     with open("raw.json", "w") as f:
#         json.dump(raw, f, indent=4)