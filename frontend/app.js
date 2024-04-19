// async function fetchJobVacancies() {
//     try {
//         const response = await fetch('https://job-api-cv1f.onrender.com/data/');
//         if (!response.ok) {
//             throw new Error('Failed to fetch job vacancies');
//         }
//         const vacancies = await response.json();
//         displayVacancies(vacancies);
//     } catch (error) {
//         console.error('Error fetching job vacancies:', error.message);
//     }
// }

// function displayVacancies(vacancies) {
//     const vacancyList = document.getElementById('vacancy-list');
//     vacancyList.innerHTML = '';
//     vacancies.forEach(vacancy => {
//         const vacancyItem = document.createElement('li');
//         vacancyItem.classList.add('vacancy-item');
//         vacancyItem.innerHTML = `
//             <h2>${vacancy.company}</h2>
//             <p><strong>Position:</strong> ${vacancy.vacancy}</p>
//             <p><strong>Apply Link:</strong> <a href="${vacancy.apply_link}" target="_blank">${vacancy.apply_link}</a></p>
//             <p><strong>Scrape Date:</strong> ${new Date(vacancy.scrape_date).toLocaleString()}</p>
//             `;
//         vacancyList.appendChild(vacancyItem);
//     });
// }


// async function searchVacancies() {
//     const searchInputCompany = document.getElementById('search-input-company').value;
//     const searchInputPosition = document.getElementById('search-input-position').value;

//     // Construct the base URL
//     let url = 'https://job-api-cv1f.onrender.com/data/?';

//     // Add company parameter if it's provided
//     if (searchInputCompany) {
//         url += `company=${encodeURIComponent(searchInputCompany)}&`;
//     }

//     // Add position parameter if it's provided
//     if (searchInputPosition) {
//         url += `position=${encodeURIComponent(searchInputPosition)}`;
//     }

//     try {
//         const response = await fetch(url);
//         if (!response.ok) {
//             throw new Error('Failed to fetch job vacancies');
//         }
//         const vacancies = await response.json();
//         displayVacancies(vacancies);
//     } catch (error) {
//         console.error('Error fetching job vacancies:', error.message);
//     }
// }

// document.getElementById('search-button').addEventListener('click', searchVacancies);

// window.onload = function () {
//     fetchJobVacancies();
//     toggleMode(); // Initially toggle mode to set the default mode
// };

// // Function to toggle between light and dark modes
// function toggleMode() {
//     const body = document.body;
//     body.classList.toggle('light-mode'); // Toggle light mode
//     body.classList.toggle('dark-mode'); // Toggle dark mode
// }

// // Event listener for mode toggle button
// document.getElementById('toggle-mode-button').addEventListener('click', toggleMode);


let currentPage = 1;
const itemsPerPage = 10; 

// Function to fetch job vacancies with pagination
async function fetchJobVacancies() {
    try {
        const response = await fetch(`https://job-api-cv1f.onrender.com/data/?page=${currentPage}&items_per_page=${itemsPerPage}`);
        if (!response.ok) {
            throw new Error('Failed to fetch job vacancies');
        }
        const vacancies = await response.json();
        displayVacancies(vacancies);
    } catch (error) {
        console.error('Error fetching job vacancies:', error.message);
    }
}

// Function to display job vacancies
function displayVacancies(vacancies) {
    const vacancyList = document.getElementById('vacancy-list');
    vacancyList.innerHTML = '';
    vacancies.forEach(vacancy => {
        const vacancyItem = document.createElement('li');
        vacancyItem.classList.add('vacancy-item');
        vacancyItem.innerHTML = `
            <h2>${vacancy.company}</h2>
            <p><strong>Position:</strong> ${vacancy.vacancy}</p>
            <p><strong>Apply Link:</strong> <a href="${vacancy.apply_link}" target="_blank">${vacancy.apply_link}</a></p>
            <p><strong>Scrape Date:</strong> ${new Date(vacancy.scrape_date).toLocaleString()}</p>
            `;
        vacancyList.appendChild(vacancyItem);
    });
}

// Function to perform search based on input
async function searchVacancies() {
    const searchInputCompany = document.getElementById('search-input-company').value;
    const searchInputPosition = document.getElementById('search-input-position').value;

    // Construct the base URL
    let url = `https://job-api-cv1f.onrender.com/data/?page=${currentPage}&items_per_page=${itemsPerPage}&`;

    // Add company parameter if provided
    if (searchInputCompany) {
        url += `company=${encodeURIComponent(searchInputCompany)}&`;
    }

    // Add position parameter if provided
    if (searchInputPosition) {
        url += `position=${encodeURIComponent(searchInputPosition)}`;
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Failed to fetch job vacancies');
        }
        const vacancies = await response.json();
        displayVacancies(vacancies);
    } catch (error) {
        console.error('Error fetching job vacancies:', error.message);
    }
}

// Event listener for search button
document.getElementById('search-button').addEventListener('click', searchVacancies);

// Event listener for mode toggle button
document.getElementById('toggle-mode-button').addEventListener('click', toggleMode);

// Function to toggle between light and dark modes
function toggleMode() {
    const body = document.body;
    body.classList.toggle('light-mode'); // Toggle light mode
    body.classList.toggle('dark-mode'); // Toggle dark mode
}

// Event listener for previous page button
document.getElementById('prev-page').addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        fetchJobVacancies();
        document.getElementById('page-number').value = currentPage;
    }
});

// Event listener for next page button
document.getElementById('next-page').addEventListener('click', () => {
    currentPage++;
    fetchJobVacancies();
    document.getElementById('page-number').value = currentPage;
});

// Event listener for manual page number input
document.getElementById('page-number').addEventListener('change', () => {
    const pageNumber = parseInt(document.getElementById('page-number').value);
    if (pageNumber >= 1) {
        currentPage = pageNumber;
        fetchJobVacancies();
    } else {
        document.getElementById('page-number').value = currentPage;
    }
});

// Fetch job vacancies on page load
window.onload = function () {
    fetchJobVacancies(); // Fetch the initial 10 job vacancies
    toggleMode(); // Initially toggle mode to set the default mode
};
