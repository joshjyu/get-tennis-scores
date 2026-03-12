import aiohttp
from typing import Any, Dict, Optional


class EspnApiError(Exception):
    """
    Exception raised for ESPN API connection or HTTP errors.
    """

    pass


class EspnClient:
    """
    Class that represents the client for interacting with the ESPN hidden
    API ecosystem.
    """

    def __init__(self) -> None:
        """
        Initializes the ESPN client.

        Parameters:
          None

        Returns:
          None
        """
        # Define both ATP & WTA endpoints
        self._atpUrlAddress = (
            "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"
        )
        self._wtaUrlAddress = (
            "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard"
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """
        Retrives the active network session, or creates one if it does not exist.

        Parameters:
          None

        Returns:
          aiohttp.ClientSession - The active asynchronous HTTP session.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_wta_scores(self) -> Dict[str, Any]:
        """
        Fetches the current WTA scoreboard data from ESPN.

        Parameters:
          None

        Returns:
          Dict[str, Any] - The raw JSON response as a dictionary.
        """
        try:
            session = await self.get_session()
            async with session.get(self._wtaUrlAddress) as apiResponse:
                # Check for good response
                if apiResponse.status == 200:
                    return await apiResponse.json()
                # Otherwise raise error
                raise EspnApiError(f"HTTP {apiResponse.status}")
        except Exception as e:
            raise EspnApiError(f"Network error: {str(e)}")

    async def fetch_atp_scores(self) -> Dict[str, Any]:
        """
        Fetches the current ATP scoreboard data from ESPN.

        Parameters:
          None

        Returns:
          Dict[str, Any] - The raw JSON response as a dictionary.
        """
        try:
            session = await self.get_session()
            async with session.get(self._atpUrlAddress) as apiResponse:
                # Check for good response
                if apiResponse.status == 200:
                    return await apiResponse.json()
                # Otherwise raise error
                raise EspnApiError(f"HTTP {apiResponse.status}")
        except Exception as e:
            raise EspnApiError(f"Network error: {str(e)}")
