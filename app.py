from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Collapsible, Static
from textual.containers import VerticalScroll, Vertical
from espn_client import EspnClient
from typing import Any, Dict

# CONSTANTS
REFRESH_INTERVAL = 60  # seconds
NAME_WIDTH = 45  # character width for player names


class MatchCard(Static):
    """
    A custom widget to display a multi-line match score box.
    """

    def __init__(self, matchData: Dict[str, Any], **kwargs: Any) -> None:
        """
        Initializes the MatchCard.

        Parameters:
          matchData - Dictionary containing match information from ESPN
          kwargs - Additional arguments for the Static widget

        Returns:
          None
        """
        super().__init__(**kwargs)
        self._matchData = matchData
        self._scoreText = self._format_match()

    def update_data(self, newMatchData: Dict[str, Any]) -> None:
        """
        Updates the internal data and refreshes the display if needed.

        Parameters:
          newMatchData - The latest dictionary of match information.

        Returns:
          None
        """
        self._matchData = newMatchData
        newText = self._format_match()
        if self._scoreText != newText:
            self._scoreText = newText
            self.update(self._scoreText)

    def _format_match(self) -> str:
        """
        Formats the multi-line display string for the match.

        Parameters:
          None

        Returns:
          str - The formatted string representing the match box.
        """
        roundName = self._matchData.get("round", {}).get("displayName", "N/A")
        competitors = self._matchData.get("competitors", [])

        # Start the match box with the name of the round
        lines = [f"{roundName}"]

        for comp in competitors:
            # Get player name
            name = comp.get("athlete", {}).get("displayName", "TBD")

            # Get set scores
            scores = []
            for scoreDict in comp.get("linescores", []):
                rawValue = scoreDict.get("value", "")

                # Convert score to int (default is float), then to str
                try:
                    intValue = int(float(rawValue))
                    scores.append(str(intValue))
                except (ValueError, TypeError):
                    scores.append("-")

            scoreString = "  ".join(scores)

            # Join the player name with player's set score
            lines.append(f"{name:{NAME_WIDTH}} {scoreString}")

        return "\n".join(lines)  # Add lines on top of each other

    def render(self) -> str:
        """
        Renders the widget's content

        Parameters:
          None

        Returns:
          str - The text to be displayed by the static widget.
        """
        return self._scoreText


class TennisApp(App):
    """
    Main application class for the Tennis Scores TUI.
    """

    # Map keys to actions
    BINDINGS = [("q", "quit", "Quit")]

    # Link to CSS file
    CSS_PATH = "styles.tcss"

    def __init__(self) -> None:
        """
        Initializes the Tennis app.

        Parameters:
          None

        Returns:
          None
        """
        super().__init__()
        self._espnClient = EspnClient()

    def compose(self) -> ComposeResult:
        """
        Composes the UI widgets for the app.

        Parameters:
          None

        Returns:
          ComposeResult - The widgets to be displayed.
        """
        yield Header()
        yield VerticalScroll(id="tournamentContainer")
        yield Footer()

    async def on_mount(self) -> None:
        """
        Event handler called when the app is mounted.

        Parameters:
          None

        Returns:
          None
        """
        # First run
        await self.update_scores()
        # Refresh scores every x seconds
        self.set_interval(REFRESH_INTERVAL, self.update_scores)

    async def _find_or_create_tournament(
        self, container: VerticalScroll, eventId: str, title: str
    ) -> Collapsible:
        """
        Finds an existing Collapsible or creates a new one.
        """
        for child in container.children:
            if isinstance(child, Collapsible) and child.id == f"event_{eventId}":
                return child

        # Create a dedicated container to hold the dynamically loaded matches
        matchContainer = Vertical(id=f"matches_{eventId}")

        # Pass the container into Collapsible
        newCollapsible = Collapsible(
            matchContainer, title=title, id=f"event_{eventId}", collapsed=True
        )
        await container.mount(newCollapsible)
        return newCollapsible

    async def _update_match_in_tournament(
        self,
        tournamentNode: Collapsible,
        eventId: str,
        matchId: str,
        matchData: Dict[str, Any],
    ) -> None:
        """
        Finds a MatchCard to update or creates a new one inside the tournament.
        """
        # Locate the internal Vertical container
        matchContainer = tournamentNode.query_one(f"#matches_{eventId}", Vertical)

        # Search children of the Collapsible
        for child in matchContainer.children:
            if isinstance(child, MatchCard) and child.id == f"match_{matchId}":
                # Patch the existing card
                child.update_data(matchData)
                return

        # If not found, mount a new card
        newCard = MatchCard(matchData, id=f"match_{matchId}")
        await matchContainer.mount(newCard)

    async def update_scores(self) -> None:
        """
        Fetches fresh data and incrementally updates the UI.

        Parameters:
          None

        Returns:
          None
        """
        container = self.query_one("#tournamentContainer", VerticalScroll)

        # Fetch the fresh data
        wtaData = await self._espnClient.fetch_wta_scores()
        wtaEvents = wtaData.get("events", [])

        # Loop through events to extract data
        # events -> groupings -> competitions -> matches
        # Groupings usually separate events (ie Women's singles vs doubles, etc)
        # Competitions contain matches
        for event in wtaEvents:
            eventId = event.get("id", "UnknownID")
            tournamentName = event.get("name", "Unknown Tournament")
            locationVenue = event.get("venue", {}).get(
                "displayName", "Unknown Location"
            )
            tournamentLabel = f"{tournamentName} ({locationVenue})"

            # Get or Create the Tournament Block (incremental)
            tournamentNode = await self._find_or_create_tournament(
                container, eventId, tournamentLabel
            )

            groupings = event.get("groupings", [])
            for group in groupings:
                groupMeta = group.get("grouping", {})

                # Women's singles data
                if groupMeta.get("slug") == "womens-singles":
                    competitions = group.get("competitions", [])

                    for match in competitions:
                        # Get match ID
                        matchId = match.get("id", "UnknownMatchID")

                        # Update or create the Match Card (incremental)
                        await self._update_match_in_tournament(
                            tournamentNode, eventId, matchId, match
                        )


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
