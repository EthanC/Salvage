import base64
import logging
from datetime import datetime
from os import environ
from pathlib import Path
from sys import exit, stdout

import dotenv
from discord_webhook import DiscordEmbed, DiscordWebhook
from github.AuthenticatedUser import AuthenticatedUser
from github.ContentFile import ContentFile
from github.Repository import Repository
from loguru import logger
from loguru_discord import DiscordSink

from handlers.intercept import Intercept
from services.git import Authenticate, DeleteFile, GetFiles, GetRepository, SaveFile


def Start() -> None:
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
            level=environ["LOG_DISCORD_WEBHOOK_LEVEL"],
            backtrace=False,
        )

        logger.success(f"Enabled logging to Discord webhook")
        logger.trace(url)

    local: dict[str, dict[str, str]] = GetLocalFiles()

    git: AuthenticatedUser | None = Authenticate(environ["GITHUB_ACCESS_TOKEN"])

    if not git:
        logger.debug("Exiting due to null GitHub user")

        return

    repo: Repository | None = GetRepository(environ["GITHUB_REPOSITORY"], git)

    if not repo:
        logger.debug("Exiting due to null GitHub repository")

        return

    remote: dict[str, dict[str, str]] = GetRemoteFiles(repo)

    CompareFiles(local, remote, repo)

    logger.info(
        f"Finished processing {len(local):,} local / {len(remote):,} remote files"
    )


def GetLocalFiles() -> dict[str, dict[str, str]]:
    """Return a dictionary containing files from the local stacks directory."""

    stacks: dict[str, dict[str, str]] = {}
    directory: Path = Path("./stacks")

    if not directory.exists():
        logger.error(f"Failed to locate local stacks directory {directory.resolve()}")

        return stacks

    for file in directory.glob("**/compose.yaml"):
        stack: str = file.relative_to("./stacks").parts[0]

        stacks[stack] = {
            "stack": stack,
            "filename": file.name,
            "filepath": str(file.relative_to("./stacks")).replace("\\", "/"),
            "content": file.read_text(),
        }

        logger.debug(f"Found file {stacks[stack]["filepath"]} in local stacks")
        logger.trace(file.resolve())
        logger.trace(stacks[stack])

    logger.info(f"Found {len(stacks):,} files in local stacks")

    return stacks


def GetRemoteFiles(repo: Repository) -> dict[str, dict[str, str]]:
    """Return a dictionary containing files from the remote stacks directory."""

    stacks: dict[str, dict[str, str]] = {}
    files: list[ContentFile] = GetFiles(repo)

    for file in files:
        stack: str = file.path.split("/")[0]

        stacks[stack] = {
            "stack": stack,
            "filename": file.name,
            "filepath": file.path,
            "content": base64.b64decode(file.content).decode("UTF-8"),
            "sha": file.sha,
        }

        logger.debug(
            f"Found file {stacks[stack]["filepath"]} in GitHub repository {repo.full_name} stacks"
        )
        logger.trace(file.html_url)
        logger.trace(stacks[stack])

    logger.info(
        f"Found {len(stacks):,} files in GitHub repository {repo.full_name} stacks"
    )

    return stacks


def CompareFiles(
    local: dict[str, dict[str, str]],
    remote: dict[str, dict[str, str]],
    repo: Repository,
) -> None:
    """
    Compare files within the local and remote stack directories.

    If a local file differs from its remote counterpart, save the file
    to the configured GitHub repository and notify about changes. Any
    remote files that are not present locally will be deleted.
    """

    for stack in local:
        new: dict[str, str] = local[stack]
        old: dict[str, str] | None = remote.get(stack)

        if not old:
            url: str | None = SaveFile(repo, new["filepath"], new["content"])

            if url:
                new["url"] = url

                Notify(new, "Created")

                logger.success(
                    f"Created file {new["filepath"]} in GitHub repository {repo.full_name}"
                )

            continue

        if new["content"] == old["content"]:
            logger.info(f"Detected no changes to file {new["filepath"]}")

            continue

        url: str | None = SaveFile(repo, new["filepath"], new["content"], old["sha"])

        if url:
            new["url"] = url

            Notify(new, "Modified")

            logger.success(
                f"Modified file {new["filepath"]} in GitHub repository {repo.full_name}"
            )

    for stack in remote:
        if not local.get(stack):
            url: str | None = DeleteFile(
                repo, remote[stack]["filepath"], remote[stack]["sha"]
            )

            if url:
                remote[stack]["url"] = url

                Notify(remote[stack], "Deleted")

                logger.success(
                    f"Deleted file {remote[stack]["filepath"]} in GitHub repository {repo.full_name}"
                )


def Notify(stack: dict[str, str], action: str) -> None:
    """Report stack changes to the configured Discord webhook."""

    if not (url := environ.get("DISCORD_WEBHOOK_URL")):
        logger.info("Discord webhook for notifications is not set")

        return

    embed: DiscordEmbed = DiscordEmbed()
    now: float = datetime.now().timestamp()

    embed.set_color("1D63ED")
    embed.set_author(
        "Salvage",
        url=f"https://github.com/EthanC/Salvage",
        icon_url="https://i.imgur.com/YPGC3In.png",
    )

    embed.add_embed_field("Stack", stack["stack"])
    embed.add_embed_field("Action", f"[{action}]({stack["url"]})")
    embed.add_embed_field("Detected", f"<t:{int(now)}:R>")
    embed.add_embed_field("File", f"```\n{stack["filepath"]}\n```", inline=False)

    embed.set_footer("Docker", icon_url="https://i.imgur.com/Rb0sSM2.png")  # pyright: ignore [reportUnknownMemberType]
    embed.set_timestamp(now)

    DiscordWebhook(url, embeds=[embed], rate_limit_retry=True).execute()


if __name__ == "__main__":
    try:
        Start()
    except KeyboardInterrupt:
        exit()
