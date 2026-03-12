from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Collapsible, Static
from textual.containers import VerticalScroll
from espn_client import EspnClient
from typing import Any, Dict

# CONSTANTS
REFRESH_INTERVAL = 30  # seconds
NAME_WIDTH = 45  # character width for player names
SERVER_SYMBOL = " * "  # Symbol to indicate player serving
WINNER_SYMBOL = "\u2714"  # Character to indicate winner of match


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
        self._matchData = matchData
        self._scoreText = self._format_match()
        super().__init__(self._scoreText, **kwargs)
        self._set_dynamic_height()

    def _set_dynamic_height(self) -> None:
        """
        Calculates the required height based on line count and updates the styles.

        Parameters:
          None

        Returns:
          None
        """
        lineCount = len(self._scoreText.split("\n"))
        self.styles.height = lineCount + 2

    def _to_superscript(self, text: str) -> str:
        """
        Converts a string of digits to unicode superscripts.

        Parameters:
          text - The string of digits to convert.

        Returns:
          str - The string converted to superscripts.
        """
        superscripts = {
            "0": "\u2070",
            "1": "\u00b9",
            "2": "\u00b2",
            "3": "\u00b3",
            "4": "\u2074",
            "5": "\u2075",
            "6": "\u2076",
            "7": "\u2077",
            "8": "\u2078",
            "9": "\u2079",
        }
        return "".join(superscripts.get(char, char) for char in text)

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
            self._set_dynamic_height()

    def _format_match(self) -> str:
        """
        Formats the multi-line display string for the match.

        Parameters:
          None

        Returns:
          str - The formatted string representing the match box.
        """
        # Get round
        roundName = self._matchData.get("round", {}).get("displayName", "N/A")
        # Get match status
        matchStatus = (
            self._matchData.get("status", {}).get("type", {}).get("description", "")
        )
        # Get player info
        competitors = self._matchData.get("competitors", [])

        # Start the match box with the name of the round
        formattedRound = f"   {roundName}"
        # Pad the round name and add the match status
        lines = [f"{formattedRound:{NAME_WIDTH}} {matchStatus}"]

        for comp in competitors:
            # Get player name
            name = comp.get("athlete", {}).get("displayName", "TBD")
            # Check if serving
            isServer = comp.get("possession", False)

            if isServer:
                name = SERVER_SYMBOL + name
            else:
                name = "   " + name

            # Get set scores
            scores = []
            for scoreDict in comp.get("linescores", []):
                rawValue = scoreDict.get("value", "")
                tiebreakValue = scoreDict.get("tiebreak")

                # Convert score to int (default is float), then to str
                try:
                    intValue = int(float(rawValue))
                    scoreStr = str(intValue)

                    # Append tiebreak score if player has 6 games
                    # This accounts for a tiebreak loser or in-progress
                    if intValue == 6 and tiebreakValue is not None:
                        tiebreakInt = int(float(tiebreakValue))
                        superStr = self._to_superscript(str(tiebreakInt))
                        scoreStr += superStr

                    # Pad string to 3 characters for vertical alignment
                    scores.append(f"{scoreStr:<3}")

                except (ValueError, TypeError):
                    scores.append("-  ")

            scoreString = "".join(scores)

            # Check if match is completed
            isCompleted = (
                self._matchData.get("status", {})
                .get("type", {})
                .get("completed", False)
            )

            if isCompleted:
                # Check if this player is the winner
                isWinner = comp.get("winner", False)
                if isWinner:
                    # Append a winner's symbol if player is the winner
                    scoreString += " " + WINNER_SYMBOL
                else:
                    scoreString += "  "

            # Join the player name with player's set score
            lines.append(f"{name:{NAME_WIDTH}} {scoreString}")

        return "\n".join(lines)  # Add lines on top of each other


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

        Parameters:
          container - The VerticalScroll container that holds the tournament widgets.
          eventId - The unique identifier string for the tournament event.
          title - The display string for the tournament Collapsible label.

        Returns:
          Collapsible - The existing or newly instantiated tournament widget.
        """
        for child in container.children:
            if isinstance(child, Collapsible) and child.id == f"event_{eventId}":
                return child

        # Create a dedicated container to hold the dynamically loaded matches
        matchContainer = Static(id=f"matches_{eventId}", classes="match-container")

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

        Parameters:
          tournamentNode - The Collapsible widget representing the tournament.
          eventId - The unique identifier string for the tournament event.
          matchId - The unique identifier string for the specific match.
          matchData - Dictionary containing the latest match information from the API.

        Returns:
          None
        """
        # Locate the internal Vertical container
        matchContainer = tournamentNode.query_one(f"#matches_{eventId}", Static)

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

                    for match in reversed(competitions):
                        # Get match ID
                        matchId = match.get("id", "UnknownMatchID")

                        # Update or create the Match Card (incremental)
                        await self._update_match_in_tournament(
                            tournamentNode, eventId, matchId, match
                        )


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
