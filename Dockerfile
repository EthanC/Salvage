FROM python:3.11.4-slim-bullseye

WORKDIR /salvage

# Install and configure Poetry
# https://github.com/python-poetry/poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Install dependencies
COPY pyproject.toml pyproject.toml
RUN poetry install

COPY . .

CMD [ "python", "salvage.py" ]
