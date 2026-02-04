# Deployment Guide

This application is containerized using Docker, making it easy to run on any machine or deploy to cloud platforms.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your machine.

## Running Locally with Docker

1.  **Build the Image:**
    Open a terminal/command prompt in this directory and run:
    ```bash
    docker build -t qa-gate-app .
    ```

2.  **Run the Container:**
    ```bash
    docker run -p 8501:8501 qa-gate-app
    ```

3.  **Access the App:**
    Open your browser and go to `http://localhost:8501`.

## Running with Docker Compose (Recommended)

If you have Docker Compose installed (usually comes with Docker Desktop):

1.  **Start the App:**
    ```bash
    docker-compose up --build
    ```

2.  **Access the App:**
    Open `http://localhost:8501`.

3.  **Stop the App:**
    Press `Ctrl+C` in the terminal.

## Deploying to Streamlit Community Cloud (Free & Easiest)

You can deploy directly from your GitHub repository for free.

1.  Push your code to a GitHub repository.
2.  Go to [Streamlit Community Cloud](https://streamlit.io/cloud).
3.  Sign in with GitHub and click "New app".
4.  Select your repository, branch, and main file path (`app.py`).
5.  Click "Deploy!".

## Deploying to Other Cloud Providers (AWS, Azure, GCP, DigitalOcean)

Since you have a `Dockerfile`, you can deploy to any container-based service.

**Example: DigitalOcean App Platform**
1.  Push code to GitHub.
2.  Create a new App in DigitalOcean.
3.  Select your GitHub repo.
4.  It will detect the Dockerfile automatically.
5.  Deploy.

**Example: AWS Elastic Beanstalk**
1.  Install EB CLI.
2.  Initialize: `eb init -p docker qa-gate-app`
3.  Create: `eb create qa-gate-env`
4.  Open: `eb open`
