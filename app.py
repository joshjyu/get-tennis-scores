from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
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
        # Temporary score display
        yield Static("Fetching scores...", id="scoreDisplay")
        yield Footer()

    async def on_mount(self) -> None:
        """
        Event handler called when the app is mounted.

        Parameters:
          None

        Returns:
          None
        """
        # Fetch the real data (data type = dict)
        atpData = await self._espnClient.fetch_atp_scores()

        # Extract events from data
        # May return an empty list if API changes
        atpEvents = atpData.get("events", [])
        eventCount = len(atpEvents)

        # Update the UI with a message
        statusMessage = f"Connected! Found {eventCount} ATP events today."
        self.query_one("#scoreDisplay", Static).update(statusMessage)


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
