# Job Vacancy Application

This project encompasses a robust backend API, two distinct frontend deployments, and a Telegram bot integration aimed at showcasing job vacancy data extracted from various websites. The backend is responsible for scraping job data, storing it in a PostgreSQL database, and serving this information via an API to the frontends and the Telegram bot. Below are detailed descriptions of each component involved in this setup:

## Frontend Deployments

### 1. Streamlit Frontend

Deployed using Streamlit, this frontend offers an interactive experience that allows users to explore job vacancies through a Python-driven interface.

**Key Features:**
- **Dynamic Search:** Users can search for job vacancies by company name or position, tailoring the results to their specific needs.
- **Pagination:** A user-friendly pagination system lets users navigate through extensive job listings with ease.

**Source File:**
- `frontend.py`: Manages all user interface elements and server-side interactions within the Streamlit application.

### 2. Traditional Web Frontend

This frontend is a traditional web application constructed using HTML, CSS, and JavaScript, with a deployment on [https://capit.netlify.app/](https://capit.netlify.app/).

**Key Features:**
- **Interactive Search:** Implements job search functionality using JavaScript to interact dynamically with the backend.
- **Paginated Results:** Allows users to sift through job listings via pagination controls.
- **Theme Toggling:** Users can switch between light and dark modes according to their preference.

**Source Files:**
- `index.html`: Provides the structural framework of the web interface.
- `style.css`: Applies custom styling to enhance the visual layout.
- `app.js`: Handles data fetching, content generation dynamically, and manages user interactions.

## Backend API

The backend API, powered by FastAPI, operates independently and interfaces with both frontend deployments and the Telegram bot. It serves as the conduit for job vacancy data stored within a PostgreSQL database, responding adeptly to HTTP requests.

**API Endpoint:**
- `https://job-api-cv1f.onrender.com/data/`: This endpoint fetches job vacancy data, offering filtering capabilities by company name and job position via query parameters.

## Telegram Bot Integration

The Telegram bot, accessible via a designated token, interacts with the backend API to fetch and deliver job vacancies directly through the Telegram interface. Users can send job titles to the bot and receive current vacancies in real-time.

**Features:**
- **Interactive Queries:** Users can interactively query job vacancies by sending messages to the bot.
- **Direct Links:** Provides direct links for applications, facilitating easy access to job application pages.

## Usage Instructions

### Streamlit Frontend
Access the interactive application at [https://vacancy.streamlit.app/](https://vacancy.streamlit.app/). Utilize the search functionality to filter job vacancies according to your criteria.

### Traditional Web Frontend
Visit [https://capit.netlify.app/](https://capit.netlify.app/) to explore the HTML/CSS/JavaScript version of the job search. Leverage the search features to locate jobs and use the theme toggle for a customized visual experience.

### Telegram Bot
Interact with the Telegram bot by sending job titles directly through your Telegram app to receive instant job listings.

## Development

For local development or contributions:
1. **Clone the Repository:** Obtain a copy of the source code on your local machine.
2. **Set Up the Local Development Environment:** Install all necessary dependencies. For the Streamlit app, ensure Python dependencies are met, and for the traditional web app, set up a web server (e.g., using the live-server feature in VS Code).

## Contributing

Contributions are encouraged and appreciated. To contribute:
1. **Fork the Repository:** Make a copy under your GitHub account.
2. **Create a Pull Request:** Submit your proposed changes for review.