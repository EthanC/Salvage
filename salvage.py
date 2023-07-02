import logging
from datetime import datetime
from os import environ
from sys import exit
from typing import Any, Dict, List, Self

import dotenv
from discord_webhook import DiscordEmbed, DiscordWebhook
from loguru import logger
from notifiers.logging import NotificationHandler

from handlers import Format, Intercept
from services import Git, Portainer


class Salvage:
    """
    Backup Portainer Stacks to GitHub and report changes via Discord.

    https://github.com/EthanC/Salvage
    """

    def Start(self: Self) -> None:
        """Initialize Salvage and begin primary functionality."""

        logger.info("Salvage")
        logger.info("https://github.com/EthanC/Salvage")

        if dotenv.load_dotenv():
            logger.success("Loaded environment variables")
            logger.trace(environ)

        # Reroute standard logging to Loguru
        logging.basicConfig(handlers=[Intercept()], level=0, force=True)

        if logUrl := environ.get("DISCORD_LOG_WEBHOOK"):
            if not (logLevel := environ.get("DISCORD_LOG_LEVEL")):
                logger.critical("Level for Discord webhook logging is not set")

                return

            logger.add(
                NotificationHandler(
                    "slack", defaults={"webhook_url": f"{logUrl}/slack"}
                ),
                level=logLevel,
                format="```\n{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}\n```",
            )

            logger.success(f"Enabled logging to Discord webhook")
            logger.trace(logUrl)

        Portainer.Authenticate(self)

        stacks: List[Dict[str, Any]] = Portainer.ListStacks(self)

        Git.Authenticate(self)
        Git.LoadRepository(self)

        for stack in stacks:
            name: str = stack["name"]
            filename: str = stack["filename"]

            stack["local"] = Portainer.GetStack(self, stack["id"], name)
            stack["remote"], stack["sha"] = Git.GetFile(self, filename) or (None, None)
            stack["gitUrl"] = Format.GitURL(
                self, self.gitName, self.gitRepo.name, filename
            )
            stack["isUpdate"] = False

            if stack["remote"]:
                if stack["local"] == stack["remote"]:
                    logger.info(f"No changes detected for Portainer Stack {name}")

                    continue
                else:
                    logger.info(f"Detected changes to Portainer Stack {name}")

                    stack["isUpdate"] = True

                    Git.SaveFile(self, filename, stack["local"], True, stack["sha"])
            else:
                logger.info(f"Portainer Stack {name} is not yet tracked")

                Git.SaveFile(self, filename, stack["local"], False)

            Salvage.Notify(self, stack)

        logger.success(f"Finished processing {len(stacks):,} Portainer Stacks")

    def Notify(self: Self, stack: Dict[str, Any]) -> None:
        """Report Portainer Stack updates to the configured Discord webhook."""

        if not (url := environ.get("DISCORD_NOTIFY_WEBHOOK")):
            logger.info("Discord webhook for notifications is not configured")

            return

        name: str = stack["name"]
        created: datetime = stack["created"]
        createdBy: str = stack["createdBy"]
        updated: datetime = stack["updated"]
        updatedBy: str = stack["updatedBy"]
        gitUrl: str = stack["gitUrl"]

        embed: DiscordEmbed = DiscordEmbed()

        embed.set_color("0BA5EC")
        embed.set_author(
            "Salvage",
            url=f"https://github.com/EthanC/Salvage",
            icon_url="https://i.imgur.com/YPGC3In.png",
        )
        embed.add_embed_field("Stack", f"[{name}]({gitUrl})")

        if stack["isUpdate"]:
            embed.add_embed_field(
                "Updated", f"{Format.Relative(self, updated)} by {updatedBy}"
            )
        else:
            embed.add_embed_field(
                "Created", f"{Format.Relative(self, created)} by {createdBy}"
            )

        embed.set_footer(text="Portainer", icon_url="https://i.imgur.com/6MtNjWh.png")
        embed.set_timestamp(datetime.now().timestamp())

        DiscordWebhook(url, embeds=[embed], rate_limit_retry=True).execute()


if __name__ == "__main__":
    try:
        Salvage.Start(Salvage)
    except KeyboardInterrupt:
        exit()
