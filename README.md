# Job Vacancy Application

This project includes two separate frontend deployments and a backend API that provides job vacancy data. Below are details on each part of the project:

## Frontend Deployments

### 1. Streamlit Frontend

The first frontend is built with Streamlit and is deployed at [https://vacancy.streamlit.app/](https://vacancy.streamlit.app/). It provides an interactive way to browse job vacancies via a Python-driven interface.

**Key Features:**
- Search job vacancies by company name or position.
- Navigate through the results using pagination.

**Source File:**
- `frontend.py`: This script powers the Streamlit application, handling UI elements and server-side logic.

### 2. Traditional Web Frontend

The second frontend is a traditional web application built using HTML, CSS, and JavaScript, deployed at [https://capit.netlify.app/](https://capit.netlify.app/).

**Key Features:**
- Job search functionality implemented with JavaScript fetching data from the backend.
- Pagination to browse through pages of results.
- Light and dark mode toggling for user preference.

**Source Files:**
- `index.html`: The main HTML document providing the structure of the web interface.
- `style.css`: CSS file for styling the web interface.
- `app.js`: JavaScript file handling the fetching of data, dynamic content generation, and user interactions.

## Backend API

The backend API is built with FastAPI and is hosted separately. It responds to HTTP requests from both frontends and serves job vacancy data from a PostgreSQL database.

**API Endpoint:**
- `https://job-api-cv1f.onrender.com/data/`: Endpoint to fetch job vacancy data, which supports filtering by company and position through query parameters.

## Usage Instructions

### Streamlit Frontend
Visit [https://vacancy.streamlit.app/](https://vacancy.streamlit.app/) to start interacting with the application. Use the search fields to filter job vacancies as per your requirement.

### Traditional Web Frontend
Go to [https://capit.netlify.app/](https://capit.netlify.app/) for the HTML/CSS/JavaScript version of the job search. Use the search functionality to find jobs and toggle the theme using the button provided.

## Development

To run these applications locally or contribute to development, you will need to clone the repository and set up a local development environment with the required dependencies for Python (Streamlit app) and ensure you have a web server for the traditional web app (e.g., using live-server in VSCode).

## Contributing

Contributions to this project are welcome. Please fork the repository and submit a pull request with your enhancements or fixes.
