from datetime import datetime
from os import environ
from sys import exit
from typing import Any, Dict, List, Optional, Self

import httpx
from httpx import Response
from loguru import logger


class Portainer:
    """Class to integrate with the Portainer API."""

    def Authenticate(self: Self) -> None:
        """
        Authenticate with Portainer using the configured credentials and
        retrieve a JWT token for further API requests.
        """

        address: Optional[str] = environ.get("PORTAINER_ADDRESS")
        port: str = environ.get("PORTAINER_PORT")

        self.pAddress: str = f"https://{address}:{port}"

        try:
            res: Response = httpx.post(
                f"{self.pAddress}/api/auth",
                json={
                    "username": environ.get("PORTAINER_USERNAME"),
                    "password": environ.get("PORTAINER_PASSWORD"),
                },
                # By default, Portainer uses a self-signed certificate.
                # https://docs.portainer.io/advanced/ssl
                verify=False,
            )

            res.raise_for_status()

            logger.trace(res.text)

            if not (jwt := res.json().get("jwt")):
                raise ValueError("JWT token not found in response")
        except Exception as e:
            logger.opt(exception=e).critical("Failed to authenticate with Portainer")

            exit(1)

        self.pJWT: str = jwt

        logger.success("Authenticated with Portainer")
        logger.trace(self.pJWT)

    def ListStacks(self: Self) -> List[Dict[str, Any]]:
        """Returns an array of Stacks from the configured Portainer instance."""

        stacks: List[Dict[str, Any]] = []

        try:
            res: Response = httpx.get(
                f"{self.pAddress}/api/stacks",
                headers={"Authorization": f"Bearer {self.pJWT}"},
                # By default, Portainer uses a self-signed certificate.
                # https://docs.portainer.io/advanced/ssl
                verify=False,
            )

            res.raise_for_status()

            logger.trace(res.text)

            if not isinstance(res.json(), list):
                raise ValueError("response is not an array")
        except Exception as e:
            logger.opt(exception=e).error("Failed to fetch Stacks from Portainer")

            return stacks

        for entry in res.json():
            logger.trace(entry)

            name: str = entry["Name"]

            stacks.append(
                {
                    "id": entry["Id"],
                    "name": name,
                    "filename": f"{name}.yml",
                    "created": datetime.fromtimestamp(
                        entry["CreationDate"]
                    ).astimezone(),
                    "createdBy": entry["CreatedBy"],
                    "updated": None,
                    "updatedBy": None,
                }
            )

            # Set updated fields for Stack if they exist
            if (ts := entry["UpdateDate"]) != 0:
                stacks[-1]["updated"] = datetime.fromtimestamp(ts).astimezone()
                stacks[-1]["updatedBy"] = entry["UpdatedBy"]

        logger.info(f"Found {len(stacks):,} Portainer Stacks")
        logger.trace(stacks)

        return stacks

    def GetStack(self: Self, id: int, name: str) -> str:
        """
        Return the Docker Compose YAML file contents for the requested
        Portainer Stack.
        """

        content: Optional[str] = None

        try:
            res: Response = httpx.get(
                f"{self.pAddress}/api/stacks/{id}/file",
                headers={"Authorization": f"Bearer {self.pJWT}"},
                # By default, Portainer uses a self-signed certificate.
                # https://docs.portainer.io/advanced/ssl
                verify=False,
            )

            res.raise_for_status()

            logger.trace(res.text)

            if not (content := res.json().get("StackFileContent")):
                raise ValueError("Stack file content is null")
        except Exception as e:
            logger.opt(exception=e).error(
                f"Failed to fetch {name} Stack from Portainer"
            )

            return

        logger.info(f"Fetched {name} Stack from Portainer")
        logger.trace(content)

        return content
