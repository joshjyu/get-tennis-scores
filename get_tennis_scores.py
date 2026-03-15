# SPDX-License-Identifier: MIT
# Copyright (c) 2026 joshjyu

from models import TourData, Match, Event
from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Collapsible, Static, Input, Label
from textual.containers import VerticalScroll, Horizontal
from textual.validation import Integer
from api_client import ApiClient, ApiError
from typing import Any

# CONSTANTS
DEFAULT_THEME = "nord"  # Default theme string
DEFAULT_REFRESH_INTERVAL = 30  # Seconds
MIN_REFRESH_INTERVAL = 10  # Seconds
CARD_WIDTH = 67  # Match card minimum width
NAME_WIDTH = 40  # Character width for player names
SERVER_SYMBOL = " * "  # Symbol to indicate player serving
WINNER_SYMBOL = "\u2714"  # Symbol to indicate winner of match


class MatchCard(Static):
    """
    A custom widget to display a multi-line match score box.
    """

    def __init__(self, matchData: Match, **kwargs: Any) -> None:
        """
        Initializes the MatchCard.

        Parameters:
          matchData - Dictionary containing match information
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

    def update_data(self, newMatchData: Match) -> None:
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
        matchStatus = self._matchData.status.type.description
        # Get player info
        competitors = self._matchData.competitors

        # Only display the round name for Scheduled matches
        roundLabel = ""
        if matchStatus == "Scheduled":
            roundLabel = self._matchData.round.displayName

        # Add the match status (and round name if applicable)
        lines = [f"{'':8}{roundLabel:<{NAME_WIDTH-8}} {matchStatus}"]

        for comp in competitors:
            # Get player name and seed and prepend seed to player's name
            name = comp.athlete.shortName
            seed = comp.curatedRank.current

            seedText = ""
            # Check seed between 0 and 99 in case a placeholder seed exists
            if seed and 0 < seed < 99:
                seedText = f"({seed})"

            paddedSeed = f"{seedText:<5}"  # 5 characters wide, left-aligned
            name = f"{paddedSeed}{name}"

            # Check if serving
            if comp.possession:
                name = SERVER_SYMBOL + name
            else:
                name = "   " + name

            # Get set scores
            scores = []
            for scoreObj in comp.linescores:
                rawValue = scoreObj.value
                tiebreakValue = scoreObj.tiebreak

                # Convert score to int (default is float), then to str
                if rawValue is not None:
                    intValue = int(rawValue)
                    scoreStr = str(intValue)

                    if intValue == 6 and tiebreakValue is not None:
                        tiebreakInt = int(tiebreakValue)
                        superStr = self._to_superscript(str(tiebreakInt))
                        scoreStr += superStr

                    scores.append(f"{scoreStr:<3}")
                else:
                    scores.append("-  ")

            scoreString = "".join(scores)

            # Check if match is completed
            isCompleted = self._matchData.status.type.completed
            if isCompleted:
                if comp.winner:
                    # Append winner symbol to winner
                    scoreString += " " + WINNER_SYMBOL
                else:
                    scoreString += "  "

            # Join the player name with player's scores
            lines.append(f"{name:{NAME_WIDTH}} {scoreString}")

        return "\n".join(lines)  # Add lines on top of each other


class TennisApp(App):
    """
    Main application class for the Tennis Scores TUI.
    """

    BINDINGS = [("q", "quit", "Quit")]
    CSS_PATH = "styles.tcss"
    AUTO_FOCUS = None  # Disable automatic focusing on startup
    TITLE = "Get Tennis Scores"  # Title for the Header widget

    def __init__(self) -> None:
        """
        Initializes the Tennis app.

        Parameters:
          None

        Returns:
          None
        """
        super().__init__()
        self._apiClient = ApiClient()
        self._refresh_interval = DEFAULT_REFRESH_INTERVAL
        self._update_timer = None

    def compose(self) -> ComposeResult:
        """
        Composes the UI widgets for the app.

        Parameters:
          None

        Returns:
          ComposeResult - The widgets to be displayed.
        """
        yield Header()

        # Settings row
        with Horizontal(id="settingsContainer"):
            yield Label("Refresh Interval (seconds):", id="refreshLabel")
            yield Input(
                value=str(self._refresh_interval),
                type="integer",
                validators=[Integer(minimum=MIN_REFRESH_INTERVAL)],
                id="refreshInput",
            )

        # Main container
        with VerticalScroll(id="tournamentContainer"):
            # ATP section
            with Collapsible(
                title="ATP Tournaments", id="atpCollapsible", collapsed=False
            ):
                # Mount ATP tournament collapsibles inside
                yield Static(id="atpContainer")
            # WTA section
            with Collapsible(
                title="WTA Tournaments", id="wtaCollapsible", collapsed=False
            ):
                # Mount individual WTA tournament collapsibles inside wtaContainer
                yield Static(id="wtaContainer")

        yield Footer()

    async def on_mount(self) -> None:
        """
        Event handler called when the app is mounted.

        Parameters:
          None

        Returns:
          None
        """
        # Default theme
        self.theme = DEFAULT_THEME
        # First run
        await self.update_scores()
        # Reference to the refresh interval timer
        self._update_timer = self.set_interval(
            self._refresh_interval, self.update_scores
        )

    async def on_unmount(self) -> None:
        """
        Event handler called when the app is unmounted.
        Closes the active network session.

        Parameters:
          None

        Returns:
          None
        """
        await self._apiClient.close_session()

    def on_input_submitted(self, inputEvent: Input.Submitted) -> None:
        """
        Handles the event when the user presses Enter in the Input widget.

        Parameters:
          inputEvent - The integer data the user submits in the Input widget.

        Returns:
          None
        """
        if inputEvent.input.id == "refreshInput":
            # Validate input
            result = inputEvent.validation_result
            if result is None or not result.is_valid:
                self.notify(
                    f"Interval must be an integer of at least {MIN_REFRESH_INTERVAL} seconds.",
                    title="Invalid Input",
                    severity="error",
                )
                # Revert to previous valid value if input invalid
                inputEvent.input.value = str(self._refresh_interval)
                return

            new_interval = int(inputEvent.value)

            if new_interval != self._refresh_interval:
                self._refresh_interval = new_interval

                # Stop existing timer and create a new one with updated interval
                if self._update_timer is not None:
                    self._update_timer.stop()

                self._update_timer = self.set_interval(
                    self._refresh_interval, self.update_scores
                )

                self.notify(
                    f"Refresh interval updated to {self._refresh_interval} seconds.",
                    title="Settings Saved",
                )

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
        matchData: Match,
    ) -> None:
        """
        Finds a MatchCard to update or creates a new one inside the tournament.
        If its required container has changed, removes the old card and remounts
        it in the propert container.

        Parameters:
          tournamentNode - The Collapsible widget representing the tournament.
          eventId - The unique identifier string for the tournament event.
          matchId - The unique identifier string for the specific match.
          matchData - Dictionary containing the latest match information from the API.

        Returns:
          None
        """
        # Determine the target container based on current match status
        matchStatus = matchData.status.type.description

        if matchStatus == "Scheduled":
            # Target the scheduled matches container
            targetContainer = tournamentNode.query_one(
                f"#scheduled_matches_{eventId}", Static
            )
        else:
            # Group active/completed matches by round
            roundName = matchData.round.displayName

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

        # Check if the match card exists and evaluate its current container
        existingCards = list(
            tournamentNode.query(MatchCard).filter(f"#match_{matchId}")
        )
        if existingCards:
            card = existingCards[0]
            # If the card is already in the correct container, update it & return
            if card.parent == targetContainer:
                card.update_data(matchData)
                return
            else:
                # The status changed (eg Scheduled -> In Progress)
                # Remove the old widget so it can be remounted in new container
                await card.remove()

        # Mount new card into chosen targetContainer
        newCard = MatchCard(matchData, id=f"match_{matchId}")
        await targetContainer.mount(newCard)

    async def _process_tour_data(self, containerId: str, tourData: TourData) -> None:
        """
        Processes tournament data for a specific tour (ATP, WTA) and updates the UI.

        Parameters:
          containerId - The ID of the Static container for the tour.
          tourData - The raw dictionary data returned from the API.

        Returns:
          None
        """
        # Map internal container IDs to slug prefixes
        tourMap = {"atpContainer": "mens", "wtaContainer": "womens"}
        tourPrefix = tourMap.get(containerId, "unknown")
        container = self.query_one(f"#{containerId}", Static)

        for event in tourData.events:
            # Get event info
            eventId = event.id
            name = event.name
            venue = event.venue.displayName
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
        event: Event,
        tourPrefix: str,
    ) -> None:
        """
        Iterates through tournament groupings to update match cards.

        Parameters:
          tournamentNode - The Collapsible representing the tournament.
          eventId - The unique ID for the tournament event.
          event - The raw event dictionary from the API.
          tourPrefix - The prefix for the event (mens vs womens).

        Returns:
          None
        """
        # events -> groupings -> competitions -> matches
        # Groupings usually separate events (ie Women's singles vs doubles, etc)
        # Competitions contain matches

        # Map tour name to specific slug
        singlesTargetSlug = f"{tourPrefix}-singles"

        for group in event.groupings:
            slug = group.grouping.slug

            # Process matches that match the tour slug
            if slug == singlesTargetSlug:
                for match in reversed(group.competitions):
                    matchId = match.id
                    await self._update_match_in_tournament(
                        tournamentNode, eventId, matchId, match
                    )

    async def update_scores(self) -> None:
        """
        Fetches fresh data and incrementally updates the UI.
        Surfaces network errors when appropriate.

        Parameters:
          None

        Returns:
          None
        """
        try:
            # Fetch and process WTA data
            wtaData = await self._apiClient.fetch_wta_scores()
            await self._process_tour_data("wtaContainer", wtaData)

            # Fetch and process ATP data
            atpData = await self._apiClient.fetch_atp_scores()
            await self._process_tour_data("atpContainer", atpData)

        except ApiError as e:
            self.notify(
                f"Data fetch failed: {e}",
                title="Connection Error",
                severity="error",
                timeout=10.0,  # seconds
            )

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
