from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable
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
        yield DataTable(id="scoreTable")
        yield Footer()

    async def on_mount(self) -> None:
        """
        Event handler called when the app is mounted.

        Parameters:
          None

        Returns:
          None
        """
        # Set up table columns
        scoreTable = self.query_one("#scoreTable", DataTable)
        scoreTable.add_columns("Tournament", "Round", "Match")

        # Run the first update immediately
        await self.update_scores()
        # Refresh scores every x seconds
        self.set_interval(REFRESH_INTERVAL, self.update_scores)

    async def update_scores(self) -> None:
        """
        Fetches fresh data and refreshes the score table.

        Parameters:
          None

        Returns:
          None
        """
        scoreTable = self.query_one("#scoreTable", DataTable)

        # Clear old rows
        scoreTable.clear()

        # Fetch the fresh data
        wtaData = await self._espnClient.fetch_wta_scores()
        wtaEvents = wtaData.get("events", [])

        # Loop through events to extract data
        # events -> groupings -> competitions -> matches
        for event in wtaEvents:
            tournamentName = event.get("name", "Unknown Tournament")
            # Groupings usually separate events (ie Women's singles,
            # Women's doubles, Mixed doubles, etc)
            groupings = event.get("groupings", [])

            for group in groupings:
                groupMeta = group.get("grouping", {})

                if groupMeta.get("slug") == "womens-singles":
                    # Competitions contain matches
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
                            matchNotes[0].get("text", "TBD")
                            if matchNotes
                            else "TBD"
                        )

                        # Clean up match details string if in progress
                        if statusDesc == "In Progress":
                            matchResult = matchResult.replace(
                                " is tied with ", " vs "
                            )
                            matchResult = matchResult.replace(" leads ", " vs ")
                            matchResult = matchResult.replace(
                                " trails ", " vs "
                            )

                        # Add info in a row to score table
                        scoreTable.add_row(
                            tournamentName, roundDisplay, matchResult
                        )


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
