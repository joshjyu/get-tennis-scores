from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable
from espn_client import EspnClient


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
        # Add columns to table
        scoreTable = self.query_one("#scoreTable", DataTable)
        scoreTable.add_columns("Event", "Location")

        # Fetch the data (type = dict)
        wtaData = await self._espnClient.fetch_wta_scores()
        # Extract events from data. May return an empty list if API changes
        wtaEvents = wtaData.get("events", [])

        # Loop through events, add rows to the table
        for event in wtaEvents:
            # Get event name
            eventName = event.get("shortName", "Unknown")

            # Location name: event -> venue -> displayName
            locationVenue = event.get("venue", {})
            locationName = locationVenue.get("displayName", "Unknown")

            scoreTable.add_row(eventName, locationName)


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
