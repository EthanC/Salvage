# Salvage

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/EthanC/Salvage/ci.yml?branch=main) ![Docker Pulls](https://img.shields.io/docker/pulls/ethanchrisp/salvage?label=Docker%20Pulls) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/ethanchrisp/salvage/latest?label=Docker%20Image%20Size)

Salvage backs up Docker Compose files to GitHub and notifies about changes.

<p align="center">
    <img src="https://i.imgur.com/sha3H6y.png" draggable="false">
</p>

## Setup

Although not required, a [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) is recommended for notifications.

Regardless of your chosen setup method, Salvage is intended for use with a task scheduler, such as [cron](https://crontab.guru/).

**Environment Variables:**

-   `LOG_LEVEL`: [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html) severity level to write to the console.
-   `LOG_DISCORD_WEBHOOK_URL`: [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL to receive log events.
-   `LOG_DISCORD_WEBHOOK_LEVEL`: Minimum [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html) severity level to forward to Discord.
-   `GITHUB_ACCESS_TOKEN` (Required): [Personal Access Token (Classic)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#personal-access-tokens-classic) for GitHub.
-   `GITHUB_REPOSITORY` (Required): Name of the private GitHub repository to store backups.
-   `DISCORD_WEBHOOK_URL`: [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL to receive Portainer Stack notifications.

### Docker (Recommended)

Modify the following `docker-compose.yaml` example file, then run `docker compose up`.

```yaml
services:
  salvage:
    container_name: salvage
    image: ethanchrisp/salvage:latest
    environment:
      LOG_LEVEL: INFO
      LOG_DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/YYYYYYYY/YYYYYYYY
      LOG_DISCORD_WEBHOOK_LEVEL: WARNING
      GITHUB_ACCESS_TOKEN: XXXXXXXX
      GITHUB_REPOSITORY: XXXXXXXX
      DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/XXXXXXXX/XXXXXXXX
    volumes:
      /home/username/stacks:/salvage/stacks:ro
```

### Standalone

Salvage is built for [Python 3.12](https://www.python.org/) or greater.

1. Install required dependencies using [Poetry](https://python-poetry.org/): `poetry install --no-root`
2. Rename `.env.example` to `.env`, then provide the environment variables.
3. Ensure the /stacks directory contains Docker Compose files.
4. Start Salvage: `python salvage.py`
