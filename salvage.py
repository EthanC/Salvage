import logging
from datetime import datetime
from os import environ
from sys import exit, stdout
from typing import Any, Dict, List, Self

import dotenv
from discord_webhook import DiscordEmbed, DiscordWebhook
from loguru import logger
from loguru_discord import DiscordSink

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

        # Reroute standard logging to Loguru
        logging.basicConfig(handlers=[Intercept()], level=0, force=True)

        if dotenv.load_dotenv():
            logger.success("Loaded environment variables")
            logger.trace(environ)

        if level := environ.get("LOG_LEVEL"):
            logger.remove()
            logger.add(stdout, level=level)

            logger.success(f"Set console logging level to {level}")

        if url := environ.get("LOG_DISCORD_WEBHOOK_URL"):
            logger.add(
                DiscordSink(url),
                level=environ.get("LOG_DISCORD_WEBHOOK_LEVEL"),
                backtrace=False,
            )

            logger.success(f"Enabled logging to Discord webhook")
            logger.trace(url)

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

        if not (url := environ.get("DISCORD_WEBHOOK_URL")):
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
