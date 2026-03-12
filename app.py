from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Collapsible, Static
from textual.containers import VerticalScroll
from espn_client import EspnClient
from typing import Any, Dict

# CONSTANTS
REFRESH_INTERVAL = 30  # seconds
CARD_WIDTH = 67  # Match card minimum width
NAME_WIDTH = 40  # character width for player names
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
        # Get match status
        matchStatus = (
            self._matchData.get("status", {}).get("type", {}).get("description", "")
        )
        # Get player info
        competitors = self._matchData.get("competitors", [])

        # Only display the round name for Scheduled matches
        roundLabel = ""
        if matchStatus == "Scheduled":
            roundLabel = self._matchData.get("round", {}).get("displayName", "N/A")

        # Add the match status (and round name if applicable)
        lines = [f"{'':8}{roundLabel:<{NAME_WIDTH-8}} {matchStatus}"]

        for comp in competitors:
            # Get player name and seed and prepend seed to player's name
            name = comp.get("athlete", {}).get("shortName", "TBD")
            seed = comp.get("curatedRank", {}).get("current")
            seedText = ""
            # Check seed between 0 and 99 in case placeholder seed exists
            if seed and str(seed).isdigit() and int(seed) > 0 and int(seed) < 99:
                seedText = f"({seed})"
            paddedSeed = f"{seedText:<5}"  # 5 characters wide, left-aligned
            name = f"{paddedSeed}{name}"

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
        with VerticalScroll(id="tournamentContainer"):
            # WTA section
            with Collapsible(
                title="WTA Tournaments", id="wtaCollapsible", collapsed=False
            ):
                # Mount individual WTA tournament collapsibles inside wtaContainer
                yield Static(id="wtaContainer")
            # ATP section
            with Collapsible(
                title="ATP Tournaments", id="atpCollapsible", collapsed=False
            ):
                # Mount ATP tournament collapsibles inside
                yield Static(id="atpContainer")
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
        self, container: Static, eventId: str, title: str
    ) -> Collapsible:
        """
        Finds an existing Collapsible or creates a new one.

        Parameters:
          container - The Static container that holds the tournament widgets.
          eventId - The unique identifier string for the tournament event.
          title - The display string for the tournament Collapsible label.

        Returns:
          Collapsible - The existing or newly instantiated tournament widget.
        """
        for child in container.children:
            if isinstance(child, Collapsible) and child.id == f"event_{eventId}":
                return child

        # Create containers for future matches
        scheduledMatchContainer = Static(
            id=f"scheduled_matches_{eventId}", classes="match-container"
        )

        # Apply current responsive grid dimensions upon initialization
        columns = max(1, self.size.width // CARD_WIDTH)
        scheduledMatchContainer.styles.grid_size_columns = columns
        scheduledMatchContainer.styles.grid_columns = "1fr " * columns

        # Wrap scheduled matches into a Collapsible
        scheduledCollapsible = Collapsible(
            scheduledMatchContainer,
            title="Scheduled Matches",
            id=f"scheduled_col_{eventId}",
            collapsed=True,
        )

        # Pass the match containers into the main tournament Collapsible
        newCollapsible = Collapsible(
            scheduledCollapsible,
            title=title,
            id=f"event_{eventId}",
            collapsed=True,
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
        # Check if the match card exists in this tournament
        for card in tournamentNode.query(MatchCard):
            if card.id == f"match_{matchId}":
                # Patch the existing card
                card.update_data(matchData)
                return

        # If it's a new card, get its status to determine its container
        matchStatus = (
            matchData.get("status", {}).get("type", {}).get("description", "")
        )

        if matchStatus == "Scheduled":
            # Target the scheduled matches container
            targetContainer = tournamentNode.query_one(
                f"#scheduled_matches_{eventId}", Static
            )
        else:
            # Group active/completed matches by round
            roundName = matchData.get("round", {}).get(
                "displayName", "Unknown Round"
            )

            # Dynamically create round ID
            roundId = roundName.replace(" ", "_").lower()
            roundContainerId = f"#round_matches_{eventId}_{roundId}"

            # Check if this round's container already exists
            existingRound = list(tournamentNode.query(roundContainerId))

            if existingRound:
                # The round exists, use it
                targetContainer = existingRound[0]
            else:
                # Round doesn't exist, create it
                targetContainer = Static(
                    id=f"round_matches_{eventId}_{roundId}",
                    classes="match-container",
                )
                columns = max(1, self.size.width // CARD_WIDTH)
                targetContainer.styles.grid_size_columns = columns
                targetContainer.styles.grid_columns = "1fr " * columns

                # Check if we have created any rounds yet
                existingRounds = list(tournamentNode.query(".round-collapsible"))
                isFirstRound = len(existingRounds) == 0

                # Wrap new round in a Collapsible
                # If it's the first round we create, leave it expanded
                newRoundCollapsible = Collapsible(
                    targetContainer,
                    title=roundName,
                    id=f"round_col_{eventId}_{roundId}",
                    classes="round-collapsible",
                    collapsed=not isFirstRound,
                )

                # Mount it to the main tournament node
                tournamentContents = tournamentNode.query_one("Contents")
                await tournamentContents.mount(newRoundCollapsible)

        # Mount new card into chosen targetContainer
        newCard = MatchCard(matchData, id=f"match_{matchId}")
        await targetContainer.mount(newCard)

    async def _process_tour_data(
        self, containerId: str, tourData: Dict[str, Any]
    ) -> None:
        """
        Processes tournament data for a specific tour (ATP, WTA) and updates the UI.

        Parameters:
          containerId - The ID of the Static container for the tour.
          tourData - The raw dictionary data returned from the ESPN API.

        Returns:
          None
        """
        # Map internal container IDs to slug prefixes
        tourMap = {"atpContainer": "mens", "wtaContainer": "womens"}
        tourPrefix = tourMap.get(containerId, "unknown")

        container = self.query_one(f"#{containerId}", Static)
        events = tourData.get("events", [])

        for event in events:
            # Get event info
            eventId = event.get("id", "UnknownId")
            name = event.get("name", "Unknown Tournament")
            venue = event.get("venue", {}).get("displayName", "Unknown")
            label = f"{name} ({venue})"  # Tournament label

            # Create or find the tournament node
            tournamentNode = await self._find_or_create_tournament(
                container, eventId, label
            )
            # Process the internal groupings
            await self._process_event_groupings(
                tournamentNode, eventId, event, tourPrefix
            )

    async def _process_event_groupings(
        self,
        tournamentNode: Collapsible,
        eventId: str,
        event: Dict[str, Any],
        tourPrefix: str,
    ) -> None:
        """
        Iterates through tournament groupings to update match cards.

        Parameters:
          tournamentNode - The Collapsible representing the tournament.
          eventId - The unique ID for the tournament event.
          event - The raw event dictionary from the ESPN API.
          tourPrefix - The prefix for the event (mens vs womens).

        Returns:
          None
        """
        # events -> groupings -> competitions -> matches
        # Groupings usually separate events (ie Women's singles vs doubles, etc)
        # Competitions contain matches

        # Map tour name to specific slug
        singlesTargetSlug = f"{tourPrefix}-singles"
        groupings = event.get("groupings", [])

        for group in groupings:
            groupMeta = group.get("grouping", {})
            slug = groupMeta.get("slug", "")

            # Process matches that match the tour slug
            if slug == singlesTargetSlug:
                competitions = group.get("competitions", [])

                for match in reversed(competitions):
                    matchId = match.get("id", "UnknownMatchID")
                    await self._update_match_in_tournament(
                        tournamentNode, eventId, matchId, match
                    )

    async def update_scores(self) -> None:
        """
        Fetches fresh data and incrementally updates the UI.

        Parameters:
          None

        Returns:
          None
        """
        # Fetch and process WTA data
        wtaData = await self._espnClient.fetch_wta_scores()
        await self._process_tour_data("wtaContainer", wtaData)

        # Fetch and process ATP data
        atpData = await self._espnClient.fetch_atp_scores()
        await self._process_tour_data("atpContainer", atpData)

    def on_resize(self, event: events.Resize) -> None:
        """
        Dynamically adjusts grid columns based on terminal width to simulate flexbox wrapping.

        Parameters:
          event - The resize event containing the new terminal dimensions.

        Returns:
          None
        """
        # Calculate max columns
        # for example, 65 min-width + 2 gutter = 67 required space per column
        columns = max(1, event.size.width // CARD_WIDTH)

        # Apply structural changes to all existing tournament containers
        for container in self.query(".match-container"):
            container.styles.grid_size_columns = columns
            container.styles.grid_columns = "1fr " * columns


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
