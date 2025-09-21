import aiohttp
import requests


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

        return await NovigAPI.__default_caller(query_type[query_parameter](arg), session)

    @staticmethod
    async def __default_caller(query, session):
        headers = {"Content-Type": "application/json"}
        async with session.post("https://gql.novig.us/v1/graphql", headers=headers, json=query) as response:
            if response.status == 200:
                return await response.json()
            return None

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
