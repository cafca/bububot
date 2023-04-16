FROM python:3.8-slim

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100
# For some reason this settings is only read from here by the pinecone client
ENV PINECONE_ENVIRONMENT=us-east1-gcp

RUN apt-get update
RUN apt-get install -y python3 python3-pip python-dev build-essential python3-venv ffmpeg

# Set the working directory
WORKDIR /code

# Copy only the requirements.txt file first
COPY requirements.txt .

# Install the dependencies from requirements.txt
RUN pip3 install -r requirements.txt

# Copy the rest of your application code
COPY . .

CMD ["python3", "-u", "bot/bot.py"]
