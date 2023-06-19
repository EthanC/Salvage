import base64
from os import environ
from sys import exit
from typing import List, Optional, Self, Tuple

from github import Github
from github.ContentFile import ContentFile
from github.NamedUser import NamedUser
from github.Repository import Repository
from loguru import logger

from handlers import Format


class Git:
    """Class to integrate with the GitHub API."""

    def Authenticate(self: Self) -> None:
        """Authenticate with GitHub using the configured credentials."""

        token: str = environ.get("GITHUB_ACCESS_TOKEN")

        if not token:
            logger.critical(
                "Cannot authenticate with GitHub, access token is not configured"
            )

            exit(1)

        self.git: Github = Github(token)

        try:
            logger.trace(self.git.get_rate_limit())
        except Exception as e:
            logger.critical(f"Failed to authenticate with GitHub, {e}")

            exit(1)

        self.gitUser: NamedUser = self.git.get_user()
        self.gitName: str = self.gitUser.login

        logger.success(f"Authenticated with GitHub as {self.gitName}")
        logger.debug(Format.GitURL(self, self.gitName))

    def LoadRepository(self: Self) -> None:
        """Fetch the configured GitHub repository for the authenticated user."""

        name: str = environ.get("GITHUB_REPOSITORY")

        if not name:
            logger.critical(
                "Cannot fetch GitHub repository, repository name is not configured"
            )

            exit(1)

        try:
            self.gitRepo: Repository = self.gitUser.get_repo(name)
        except Exception as e:
            logger.critical(
                f"Failed to fetch GitHub repository {self.gitName}/{name}, {e}"
            )

            exit(1)

        if not self.gitRepo.private:
            logger.critical(
                f"GitHub repository {self.gitName}/{name} visibility is not private"
            )
            logger.info(
                "Portainer Stacks can contain sensitive credentials, Salvage will not proceed"
            )

            exit(1)

        logger.info(f"Loaded GitHub repository {self.gitName}/{name}")
        logger.debug(Format.GitURL(self, self.gitName, name))

    def GetFile(self: Self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetch the specified file from the configured GitHub repository
        and return both its contents and blob SHA hash as a Tuple.

        Return Tuple of Nones if file does not exist.
        """

        try:
            files: List[ContentFile] = self.gitRepo.get_contents("/")

            logger.trace(files)
        except Exception as e:
            # Repository is likely empty but we do not have an Exception
            # specific to this error, so continue on; quietly.
            logger.debug(f"Failed to fetch files in GitHub repository, {e}")

            return

        for file in files:
            logger.trace(file)

            if file.name != filename:
                continue

            content: str = base64.b64decode(file.content).decode("UTF-8")

            logger.info(f"Fetched file {filename} from GitHub repository")
            logger.debug(Format.GitURL(self, self.gitName, filename))
            logger.trace(content)

            return content, file.sha

    def SaveFile(
        self: Self, filename: str, content: str, exists: bool, sha: Optional[str] = None
    ) -> None:
        """
        Update the specified file in the configured GitHub repository
        with the provided contents. If file does not exist, create it.
        """

        try:
            if exists:
                self.gitRepo.update_file(filename, f"Update {filename}", content, sha)
            else:
                self.gitRepo.create_file(filename, f"Create {filename}", content)
        except Exception as e:
            logger.error(f"Failed to save file {filename} to GitHub repository, {e}")

            return

        logger.success(f"Saved file {filename} to GitHub repository")
