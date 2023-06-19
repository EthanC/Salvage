from datetime import datetime, timezone
from typing import Optional, Self

from loguru import logger


class Format:
    """Utility containing string formatting handlers."""

    def Relative(self: Self, input: datetime) -> str:
        """
        Create a relative timestamp using Discord formatting.
        Example: "in 2 minutes" or "6 minutes ago
        """

        # Ensure object timezone is UTC
        input = input.astimezone(timezone.utc)

        result: str = f"<t:{int(input.timestamp())}:R>"

        logger.trace(f"Generated Discord relative timestamp {result}")

        return result

    def GitURL(
        self: Self,
        username: str,
        repository: Optional[str] = None,
        path: Optional[str] = None,
    ) -> str:
        """
        Return a URL to the provided GitHub resource.

        Example: "https://github.com/EthanC/Salvage/blob/main/salvage.py"
        """

        result: str = f"https://github.com/{username}"

        if repository:
            result += f"/{repository}"

        if path:
            result += f"/blob/main/{path}"

        logger.trace(f"Generated URL for GitHub file at {result}")

        return result
