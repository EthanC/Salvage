from github import Github
from github.AuthenticatedUser import AuthenticatedUser
from github.Commit import Commit
from github.ContentFile import ContentFile
from github.GithubObject import _NotSetType  # pyright: ignore [reportPrivateUsage]
from github.NamedUser import NamedUser
from github.Repository import Repository
from loguru import logger


def Authenticate(token: str) -> AuthenticatedUser | None:
    """
    Authenticate with GitHub using the configured credentials and return
    the user object.
    """

    try:
        git: Github = Github(token)
        user: NamedUser | AuthenticatedUser = git.get_user()

        logger.trace(git.get_rate_limit())

        if isinstance(user, NamedUser):
            raise RuntimeError(
                "Expected AuthenticatedUser object, received NamedUser object"
            )
    except Exception as e:
        logger.opt(exception=e).error("Failed to authenticate with GitHub")

        return

    logger.debug(f"Authenticated with GitHub as {user.login}")

    return user


def GetRepository(name: str, user: AuthenticatedUser) -> Repository | None:
    """Fetch the configured GitHub repository for the authenticated user."""

    repo: Repository | None = None

    try:
        repo = user.get_repo(name)
    except Exception as e:
        logger.opt(exception=e).error(
            f"Failed to get GitHub repository {user.login}/{name}"
        )

        return

    if not repo.private:
        logger.critical(
            f"GitHub repository {repo.full_name} visibility is not private, Salvage will not proceed"
        )

        return

    logger.debug(f"Loaded GitHub repository {repo.full_name}")

    return repo


def GetFiles(repo: Repository) -> list[ContentFile]:
    """
    Recursively search the provided GitHub repository and return a list
    containing ContentFile objects for each discovered file.
    """

    files: list[ContentFile] = []

    try:
        # Ensure contents object is a list of ContentFiles
        if isinstance(contents := repo.get_contents(""), ContentFile):
            contents = [contents]
    except Exception as e:
        logger.opt(exception=e).error(
            f"Failed to get files from GitHub repository {repo.full_name}"
        )

        return files

    while contents:
        file: ContentFile = contents.pop(0)

        if file.type == "dir":
            try:
                # Ensure dirContents object is a list of ContentFiles
                if isinstance(dirContents := repo.get_contents(file.path), ContentFile):
                    dirContents = [dirContents]
            except Exception as e:
                logger.error(
                    f"Failed to get files from directory {file.name} in GitHub repository {repo.full_name}"
                )

                continue

            contents.extend(dirContents)
        else:
            files.append(file)

    logger.debug(f"Found {len(files):,} files in GitHub repository {repo.full_name}")

    return files


def GetFile(repo: Repository, filename: str) -> ContentFile | None:
    """
    Return the ContentFile object with a matching filename from the
    provided GitHub repository.
    """

    files: list[ContentFile] = GetFiles(repo)

    for file in files:
        if file.name != filename:
            logger.trace(f"Skipping file {file.name}, filename is not {filename}")

            continue

        logger.debug(f"Fetched file {filename} from GitHub repository {repo.full_name}")

        return file


def SaveFile(
    repo: Repository, filepath: str, content: str, sha: str | None = None
) -> str | None:
    """
    Modify the specified file in the configured GitHub repository
    with the provided contents. If file does not exist, create it.

    Return the commit URL for the file if successful.
    """

    result: dict[str, ContentFile | Commit] | None = None

    try:
        if sha:
            result = repo.update_file(filepath, f"Update {filepath}", content, sha)
        else:
            result = repo.create_file(filepath, f"Create {filepath}", content)
    except Exception as e:
        logger.opt(exception=e).error(
            f"Failed to save file {filepath} to GitHub repository {repo.full_name}"
        )

        return

    logger.debug(f"Saved file {filepath} to GitHub repository {repo.full_name}")

    if (result) and (isinstance(result["commit"], Commit)):
        return result["commit"].html_url


def DeleteFile(repo: Repository, filepath: str, sha: str) -> str | None:
    """
    Delete the specified file in the configured GitHub repository.

    Return the commit URL for the file if successful.
    """

    result: dict[str, Commit | _NotSetType] | None = None

    try:
        result = repo.delete_file(filepath, f"Delete {filepath}", sha)
    except Exception as e:
        logger.opt(exception=e).error(
            f"Failed to delete file {filepath} from GitHub repository {repo.full_name}"
        )

        return

    logger.debug(f"Deleted file {filepath} from GitHub repository {repo.full_name}")

    if (result) and (isinstance(result["commit"], Commit)):
        return result["commit"].html_url
