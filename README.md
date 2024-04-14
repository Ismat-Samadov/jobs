# Job API

This project is a FastAPI-based API for accessing job vacancy data scraped from various websites. It includes a scraper module to fetch data from specific sources and store it in a PostgreSQL database, as well as an API module to serve the data via HTTP endpoints.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/Ismat-Samadov/job_api.git
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Set up your PostgreSQL database and configure the connection details in the `.env` file. You can use the provided `.env.example` file as a template.

2. Run the scraper to fetch job vacancies and store them in the database:

    ```bash
    python scraper/scraper.py
    ```

3. Start the FastAPI server to serve the API:

    ```bash
    uvicorn app.main:app --reload
    ```

4. Access the API endpoints to retrieve job vacancy data.

## API Endpoints

- `GET /`: Root endpoint that returns a welcome message.
- `GET /data/`: Endpoint to retrieve all job vacancy data.
- `GET /data/id/{id}`: Endpoint to retrieve job vacancy data by ID.
- `GET /data/company/{company}`: Endpoint to retrieve job vacancy data by company name.
- `POST /data/`: Endpoint to create new job vacancy data.
- `PUT /data/{id}`: Endpoint to update job vacancy data by ID.
- `DELETE /data/{id}`: Endpoint to delete job vacancy data by ID.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests for any improvements or bug fixes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.