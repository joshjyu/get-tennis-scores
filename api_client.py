# SPDX-License-Identifier: MIT
# Copyright (c) 2026 joshjyu

"""
Disclaimer:
This module interacts with an undocumented, unofficial API.
It is provided for educational purposes only. The author makes no guarantees
regarding the stability, legality, or terms of service compliance of these
network requests. End-users are solely responsible for any repercussions
arising from the use of this code, including IP bans or legal action from
the data provider.
"""

import aiohttp
from typing import Optional
from models import TourData
from pydantic import ValidationError


class ApiError(Exception):
    """
    Exception raised for API connection or HTTP errors.
    """

    pass


class ApiClient:
    """
    Class that represents the client for interacting with the API.
    """

    def __init__(self) -> None:
        """
        Initializes the API client.

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

    async def close_session(self) -> None:
        """
        Closes the active asynchronous HTTP session.

        Parameters:
          None

        Returns:
          None
        """
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def fetch_wta_scores(self) -> TourData:
        """
        Fetches the current WTA scoreboard data.

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
                    data = await apiResponse.json()
                    return TourData(**data)
                # Otherwise raise error
                raise ApiError(f"HTTP {apiResponse.status}")
        except ValidationError as e:
            raise ApiError(f"Schema Validation Error: {e}")
        except Exception as e:
            raise ApiError(f"Network error: {str(e)}")

    async def fetch_atp_scores(self) -> TourData:
        """
        Fetches the current ATP scoreboard data.

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
                    data = await apiResponse.json()
                    return TourData(**data)
                # Otherwise raise error
                raise ApiError(f"HTTP {apiResponse.status}")
        except ValidationError as e:
            raise ApiError(f"Schema Validation Error: {e}")
        except Exception as e:
            raise ApiError(f"Network error: {str(e)}")
