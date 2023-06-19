# Salvage

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/EthanC/Salvage/ci.yml?branch=main) ![Docker Pulls](https://img.shields.io/docker/pulls/ethanchrisp/salvage?label=Docker%20Pulls) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/ethanchrisp/salvage/latest?label=Docker%20Image%20Size)

Salvage backs up Portainer Stacks to GitHub and reports changes via Discord.

<p align="center">
    <img src="https://i.imgur.com/aaRB8Z4.png" draggable="false">
</p>

## Setup

Although not required, a [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) is recommended for notifications.

Regardless of your chosen setup method, Salvage is intended for use with a task scheduler, such as [cron](https://crontab.guru/).

**Environment Variables:**

-   `PORTAINER_ADDRESS` (Required): IP or URL for the local Portainer instance.
-   `PORTAINER_PORT` (Required): Port number for the local Portainer instance.
-   `PORTAINER_USERNAME` (Required): Username for the local Portainer instance.
-   `PORTAINER_PASSWORD` (Required): Password for the local Portainer instance.
-   `GITHUB_ACCESS_TOKEN` (Required): [Personal Access Token (Classic)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#personal-access-tokens-classic) for GitHub.
-   `GITHUB_REPOSITORY` (Required): Name of the private GitHub repository to store backups.
-   `DISCORD_NOTIFY_WEBHOOK`: [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL to receive available username notifications.
-   `DISCORD_LOG_WEBHOOK`: [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL to receive log events.
-   `DISCORD_LOG_LEVEL`: Minimum [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html) severity level to forward to Discord.

### Docker (Recommended)

Modify the following `docker-compose.yml` example file, then run `docker compose up`.

```yml
version: "3"
services:
  salvage:
    container_name: salvage
    image: ethanchrisp/salvage:latest
    environment:
      PORTAINER_ADDRESS: XXXXXXXX
      PORTAINER_PORT: 1234
      PORTAINER_USERNAME: XXXXXXXX
      PORTAINER_PASSWORD: XXXXXXXX
      GITHUB_ACCESS_TOKEN: XXXXXXXX
      GITHUB_REPOSITORY: XXXXXXXX
      DISCORD_NOTIFY_WEBHOOK: https://discord.com/api/webhooks/XXXXXXXX/XXXXXXXX
      DISCORD_LOG_WEBHOOK: https://discord.com/api/webhooks/XXXXXXXX/XXXXXXXX
      DISCORD_LOG_LEVEL: WARNING
```

### Standalone

Salvage is built for [Python 3.11](https://www.python.org/) or greater.

1. Install required dependencies using [Poetry](https://python-poetry.org/): `poetry install`
2. Rename `.env.example` to `.env`, then provide the environment variables.
3. Start Salvage: `python salvage.py`
