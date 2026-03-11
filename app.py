from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree
from espn_client import EspnClient

# CONSTANTS
REFRESH_INTERVAL = 60  # seconds


class TennisApp(App):
    """
    Main application class for the Tennis Scores TUI.
    """

    # Map keys to actions
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        """
        Initializes the Tennis app.
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
        scoreTree = Tree("WTA", id="scoreTree")
        scoreTree.root.expand()
        yield scoreTree
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

    async def update_scores(self) -> None:
        """
        Fetches fresh data and refreshes the score tree.

        Parameters:
          None

        Returns:
          None
        """
        scoreTree = self.query_one("#scoreTree", Tree)
        # Clear old branches
        scoreTree.root.remove_children()

        # Fetch the fresh data
        wtaData = await self._espnClient.fetch_wta_scores()
        wtaEvents = wtaData.get("events", [])

        # Loop through events to extract data
        # events -> groupings -> competitions -> matches
        # Groupings usually separate events (ie Women's singles vs doubles, etc)
        # Competitions contain matches
        for event in wtaEvents:
            tournamentName = event.get("name", "Unknown Tournament")
            locationVenue = event.get("venue", {}).get(
                "displayName", "Unknown Location"
            )

            # Create tournament branch
            tournamentLabel = f"{tournamentName} ({locationVenue})"
            # Start collapsed
            tournamentNode = scoreTree.root.add(tournamentLabel, expand=False)

            groupings = event.get("groupings", [])
            for group in groupings:
                groupMeta = group.get("grouping", {})
                if groupMeta.get("slug") == "womens-singles":
                    competitions = group.get("competitions", [])
                    for match in competitions:
                        # Get match round
                        roundDisplay = match.get("round", {}).get(
                            "displayName", "N/A"
                        )
                        # Get status (in progress, final, etc)
                        statusDesc = (
                            match.get("status", {})
                            .get("type", {})
                            .get("description", "")
                        )
                        # Get competitor and score info
                        matchNotes = match.get("notes", [])
                        matchResult = (
                            matchNotes[0].get("text", "TBD") if matchNotes else "TBD"
                        )
                        # Clean up match details string if in progress
                        if statusDesc == "In Progress":
                            matchResult = matchResult.replace(
                                " is tied with ", " vs "
                            )
                            matchResult = matchResult.replace(" leads ", " vs ")
                            matchResult = matchResult.replace(" trails ", " vs ")

                        # Add match as a leaf to the tournament node
                        matchLabel = f"{roundDisplay}: {matchResult}"
                        tournamentNode.add_leaf(matchLabel)


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
