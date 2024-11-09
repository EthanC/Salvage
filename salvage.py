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
        logger.trace(f"{environ=}")

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
        logger.trace(f"{url=}")

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

    results: dict[str, dict[str, str]] = {}
    directory: Path = Path("./stacks")

    if not directory.exists():
        logger.error(f"Failed to locate local stacks directory {directory.resolve()}")

        return results

    # Default pattern if GLOB_PATTERN environment variable is not set
    patterns: list[str] = ["**/compose.yaml"]

    if custom := environ.get("GLOB_PATTERNS"):
        patterns = custom.split(",")

    logger.trace(f"{patterns=}")

    for pattern in patterns:
        logger.trace(f"{pattern=}")

        for file in directory.glob(pattern):
            logger.trace(f"{file=}")

            stack: str = file.relative_to("./stacks").parts[0]
            filename: str = file.name

            results[f"{stack}/{filename}"] = {
                "stack": stack,
                "filename": filename,
                "filepath": str(file).replace("\\", "/"),
                "content": file.read_text(),
            }

            logger.debug(
                f"Found file {results[f"{stack}/{filename}"]["filepath"]} in local stacks"
            )
            logger.trace(file.resolve())
            logger.trace(f"{results[f"{stack}/{filename}"]=}")

    logger.info(f"Found {len(results):,} files in local stacks")
    logger.trace(f"{results=}")

    return results


def GetRemoteFiles(repo: Repository) -> dict[str, dict[str, str]]:
    """Return a dictionary containing files from the remote stacks directory."""

    results: dict[str, dict[str, str]] = {}
    files: list[ContentFile] = GetFiles(repo)

    for file in files:
        logger.trace(f"{file=}")

        stack: str = file.path.split("/")[1]
        filename: str = file.name

        results[f"{stack}/{filename}"] = {
            "stack": stack,
            "filename": filename,
            "filepath": file.path,
            "content": base64.b64decode(file.content).decode("UTF-8"),
            "sha": file.sha,
        }

        logger.debug(
            f"Found file {results[f"{stack}/{filename}"]["filepath"]} in GitHub repository {repo.full_name} stacks"
        )
        logger.trace(f"{file.html_url=}")
        logger.trace(f"{results[f"{stack}/{filename}"]=}")

    logger.info(
        f"Found {len(results):,} files in GitHub repository {repo.full_name} stacks"
    )
    logger.trace(f"{results=}")

    return results


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

    for file in local:
        new: dict[str, str] = local[file]
        old: dict[str, str] | None = remote.get(file)

        logger.trace(f"{file=} {new=} {old=}")

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

    for file in remote:
        logger.trace(f"{file=}")

        if not local.get(file):
            url: str | None = DeleteFile(
                repo, remote[file]["filepath"], remote[file]["sha"]
            )

            if url:
                remote[file]["url"] = url

                Notify(remote[file], "Deleted")

                logger.success(
                    f"Deleted file {remote[file]["filepath"]} in GitHub repository {repo.full_name}"
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
