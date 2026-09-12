import aiohttp
import asyncio
import os
from dotenv import load_dotenv


load_dotenv()

if not os.getenv("PROXIES"):
    raise ValueError("PROXIES env variable is not set")

PROXIES = os.getenv("PROXIES")
PROXY_LIST = PROXIES.split(",")

import logging
log = logging.getLogger(__name__)

class NovigAPI:
    async def query_caller(self, session, query_parameter, league=None, event_id=None):
        """Returns a GraphQL query based on the provided query parameter."""
        if not league and not event_id:
            raise ValueError("Please provide either a league or an event_id, not both.")

        query_type = {
            "league": self.__league_caller,
            "market": self.novig_market_caller,
        }

        if query_parameter not in query_type:
            raise ValueError(
                f"Invalid query parameter: {query_parameter}. Valid options are: {', '.join(query_type.keys())}")

        arg = league if league is not None else event_id

        return await self.__default_caller(query_type[query_parameter](arg))


    async def __default_caller(self, query, backoff=1.0):
        headers = {"Content-Type": "application/json"}

        for attempt, proxy in enumerate(PROXY_LIST, start=1):
            if "@" not in proxy:
                raise ValueError(f"Invalid proxy format: {proxy}")

            user_pass, host = proxy.split("@")
            proxy_url = f"http://{host}"
            username, password = user_pass.split(":")
            auth = aiohttp.BasicAuth(username, password)

            try:
                async with self.sem:
                    async with aiohttp.ClientSession(
                            timeout=aiohttp.ClientTimeout(total=30, connect=10)
                    ) as session:
                        async with session.post("https://gql.novig.us/v1/graphql",
                                                headers=headers,
                                                json=query,
                                                proxy=proxy_url,
                                                proxy_auth=auth,
                                                ) as response:
                            data = await response.json()
                            status = response.status

                if data.get("errors"):
                    errors = data["errors"]
                    is_timeout = any(
                        e.get("extensions", {}).get("code") == "time-limit-exceeded"
                        for e in errors
                    )
                    if is_timeout:
                        wait = backoff * (2 ** attempt)
                        await asyncio.sleep(wait)
                        continue
                    return {"data": {"event": []}}

                if status == 200:
                    return data
            except aiohttp.ClientError as e:
                log.warning("proxy %s failed: %s: %s", host, type(e).__name__, e)
                continue

        return {"data": {"event": []}}

    @staticmethod
    def __league_caller(league):
        """ Constructs a GraphQL query to fetch events for a specific league."""
        return {
            "operationName": "MyQuery",
            "query": """
            query MyQuery($league: String!) {
              event(
                where: {
                  status: { _in: ["OPEN_PREGAME"] },
                  game: { league: { _eq: $league } }
                }
              ) {
              game {
                  scheduled_start
                }
                id
                description
              }
            }
            """,
            "variables": {
                "league": league
            }
        }

    @staticmethod
    def novig_market_caller(event_id):
        """ Constructs a GraphQL query to fetch market data for a specific event."""
        return {
            "query": """
                query ($eventId: uuid!) {
                  event(
                    where: {
                      _and: [
                        { id: { _eq: $eventId } },
                        { _or: [
                          { status: { _eq: "OPEN_PREGAME" } }
                        ]}
                      ]
                    }
                  ) {
                    description
                    id
                    game {
                      scheduled_start
                    }
                    markets {
                      description
                      type
                      strike

                      player {
                        full_name
                      }

                      outcomes(
                        where: {
                          _or: [
                            { last: { _is_null: false } },
                            { available: { _is_null: false } },
                          ]
                        }
                      ) {
                        id
                        description
                        last
                        available
                        orders(
                          where: {
                            status: { _eq: "OPEN" },
                            currency: { _eq: "CASH" },
                          },
                          order_by: { price: desc }
                        ) {
                          status
                          qty
                          price
                          originalQty
                          created_at
                        }
                      }
                    }
                  }
                }
                """,
            "variables": {
                "eventId": event_id
            }
        }