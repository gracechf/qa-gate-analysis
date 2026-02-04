# QA Gate Data Analysis

This project provides tools to analyze QA Gate data exported from Jira. It includes a Python script for generating static HTML reports and a Streamlit application for interactive data exploration.

## Features

-   **Interactive Dashboard**: A powerful Streamlit app (`app.py`) featuring:
    -   **Multi-Tab Analytics**: Overview, Trends & Performance (Moving Averages), and detailed Failure Analysis.
    -   **Advanced Filtering**: Filter by date presets (Last 7/30/90 days), specific assignees, lot number search, and yield percentage thresholds.
    -   **Proactive Status Tracking**: Visual indicators for process health (🚨 Critical / ⚠️ Warning) based on yield thresholds.
    -   **Professional Exports**: One-click export to multi-sheet Excel workbooks or CSV files.
-   **Data Management**: Persistent SQLite storage with automatic deduplication on upload.
-   **Clean Architecture**: Centralized settings in `config.py` for process mapping, yield thresholds, and UI customization.
-   **Data Validation**: Built-in logic to prevent data entry errors and a Z-score based outlier detection engine.
-   **Static Reporting**: A legacy script (`analyze_qa_data.py`) for quick standalone HTML reports.

## Prerequisites

-   **Python 3.8+**
-   **Docker** (Optional, for containerized deployment)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-folder>
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running the Interactive Dashboard (Recommended)

1.  Run the Streamlit app:
    ```bash
    python -m streamlit run app.py
    ```
2.  Open your browser to `http://localhost:8501`.
3.  **Setup**: The app uses a persistent database. Use the sidebar to upload your Jira CSV files (e.g., `Jira (11).csv`) the first time you use it.

### Generating a Static Report

1.  Ensure your data file (default `Jira (11).csv`) is in the project directory.
2.  Run the analysis script:
    ```bash
    python analyze_qa_data.py
    ```
3.  Open `qa_analysis_report.html` in your browser.

## Running with Docker

1.  **Build the image:**
    ```bash
    docker build -t qa-gate-app .
    ```

2.  **Run the container:**
    ```bash
    docker run -p 8501:8501 qa-gate-app
    ```

## Project Structure

-   `app.py`: Main entry point for the Streamlit dashboard.
-   `analyze_qa_data.py`: Core logic for data processing and static report generation.
-   `requirements.txt`: Python dependencies.
-   `Dockerfile`: Configuration for building the Docker image.
-   `docker-compose.yml`: Configuration for Docker Compose.
-   `DEPLOYMENT.md`: Detailed deployment instructions.
