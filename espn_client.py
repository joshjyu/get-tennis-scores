import aiohttp
from typing import Any, Dict


class EspnClient:
    """
    Class that represents the client for interacting with the ESPN hidden
    API ecosystem.
    """

    def __init__(self) -> None:
        """
        Initializes the ESPN client.
        """
        # Define both ATP & WTA endpoints
        self._atpUrlAddress = "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"
        self._wtaUrlAddress = "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard"

    async def fetch_atp_scores(self) -> Dict[str, Any]:
        """
        Fetches the current ATP scoreboard data from ESPN.

        Parameters:
          None

        Returns:
          Dict[str, Any] - The raw JSON response as a dictionary.
        """
        async with aiohttp.ClientSession() as networkSession:
            async with networkSession.get(self._atpUrlAddress) as apiResponse:
                # Return the JSON body as a Python dictionary
                return await apiResponse.json()
