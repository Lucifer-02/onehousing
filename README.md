# OneHousing Data Scraper

## Description

This project contains a Python-based web scraper designed to extract real estate data from [onehousing.vn](https://onehousing.vn/cong-cu/dinh-gia). It systematically navigates through provinces, projects, buildings, and floors to gather apartment information. The collected data is flattened and saved into Parquet files for efficient storage and analysis.

The scraper is built using `playwright` for browser automation and `polars` for data manipulation.

## Features

- Scrapes apartment data including province, project, building, floor, and apartment name.
- Uses `playwright` for robust browser automation.
- Leverages `polars` for efficient data handling.
- Saves data in the efficient Parquet format.
- Skips projects that have already been scraped to allow for easy resumption.
- Configured to use a SOCKS5 proxy for requests.

## Prerequisites

- Python 3.12 or higher.
- A SOCKS5 proxy server running on `127.0.0.1:9050`. This is required by the current `playwright` configuration. You can use Tor or any other SOCKS5 proxy.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd onehousing
    ```

2.  **Install Python dependencies:**
    You can use `pip` with the `pyproject.toml` file:
    ```bash
    pip install .
    ```
    Or, if you are using `uv`:
    ```bash
    uv pip install .
    ```

3.  **Install Playwright browsers:**
    The first time you run `playwright`, it will prompt you to install the necessary browser binaries. You can also do this manually:
    ```bash
    playwright install
    ```

## Usage

To start the scraping process, simply run the `main.py` script:

```bash
python main.py
```

The scraper will launch a browser window and begin navigating the OneHousing website. Progress will be displayed in the console using `tqdm` progress bars.

## Data

The scraped data is saved in the `dataset/` directory. Currently, it is configured to scrape data for "TP.Hà Nội" and will create files inside `dataset/hanoi/`. Each project's data is saved in a separate Parquet file named after the project (e.g., `dataset/hanoi/VinhomesOceanPark.parquet`).

The data schema in the Parquet files is as follows:
- `project`: Name of the real estate project.
- `building`: Name of the building within the project.
- `floor`: Floor number/name.
- `apartment`: Apartment number/name.
