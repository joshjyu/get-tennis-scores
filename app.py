from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree
from textual.widgets.tree import TreeNode
from espn_client import EspnClient
from typing import Any, Dict, List, Optional

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

    def _find_or_add_node(
        self, parentNode: TreeNode, nodeID: str, label: str, expand: bool = False
    ) -> TreeNode:
        """
        Finds an existing node by its ID or adds a new one if it doesn't exist.

        Parameters:
          parentNode - The node to search within.
          nodeID - The unique ID from ESPN.
          label - The display text for the node.
          expand - Whether the node should be expanded if newly created.

        Returns:
          TreeNode - The found or newly created node.
        """
        # Search existing children for this ID
        for child in parentNode.children:
            if child.data == nodeID:
                # Update label if it changed (eg score change)
                if str(child.label) != label:
                    child.label = label
                return child

        # If not found, add it
        return parentNode.add(label, data=nodeID, expand=expand)

    async def update_scores(self) -> None:
        """
        Fetches fresh data and incrementally updates the score tree.

        Parameters:
          None

        Returns:
          None
        """
        scoreTree = self.query_one("#scoreTree", Tree)

        # Fetch the fresh data
        wtaData = await self._espnClient.fetch_wta_scores()
        wtaEvents = wtaData.get("events", [])

        # Loop through events to extract data
        # events -> groupings -> competitions -> matches
        # Groupings usually separate events (ie Women's singles vs doubles, etc)
        # Competitions contain matches
        for event in wtaEvents:
            eventID = event.get("id", "UnknownID")
            tournamentName = event.get("name", "Unknown Tournament")
            locationVenue = event.get("venue", {}).get(
                "displayName", "Unknown Location"
            )

            # Create tournament branch
            tournamentLabel = f"{tournamentName} ({locationVenue})"
            # Start collapsed
            tournamentNode = self._find_or_add_node(
                scoreTree.root, eventID, tournamentLabel, expand=False
            )

            groupings = event.get("groupings", [])
            for group in groupings:
                groupMeta = group.get("grouping", {})

                # Women's singles data
                if groupMeta.get("slug") == "womens-singles":
                    competitions = group.get("competitions", [])

                    for match in competitions:
                        # Get match ID
                        matchID = match.get("id", "UnknownMatchID")
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
                        self._find_or_add_node(tournamentNode, matchID, matchLabel)


if __name__ == "__main__":
    tennisApp = TennisApp()
    tennisApp.run()
