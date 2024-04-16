async function fetchJobVacancies() {
    try {
        const response = await fetch('https://job-api-cv1f.onrender.com/data/');
        if (!response.ok) {
            throw new Error('Failed to fetch job vacancies');
        }
        const vacancies = await response.json();
        displayVacancies(vacancies);
    } catch (error) {
        console.error('Error fetching job vacancies:', error.message);
    }
}

function displayVacancies(vacancies) {
    const vacancyList = document.getElementById('vacancy-list');
    vacancyList.innerHTML = ''; // Clear previous list items
    vacancies.forEach(vacancy => {
        const vacancyItem = document.createElement('li');
        vacancyItem.classList.add('vacancy-item');
        vacancyItem.innerHTML = `
            <h2>${vacancy.company}</h2>
            <p><strong>Position:</strong> ${vacancy.vacancy}</p>
            <p><strong>Apply Link:</strong> <a href="${vacancy.apply_link}" target="_blank">${vacancy.apply_link}</a></p>
        `;
        vacancyList.appendChild(vacancyItem);
    });
}

async function searchVacancies() {
    const searchInputCompany = document.getElementById('search-input-company').value;
    const searchInputPosition = document.getElementById('search-input-position').value;
    const url = new URL('https://job-api-cv1f.onrender.com/data/position/');
    const params = { position: searchInputPosition };
    url.search = new URLSearchParams(params).toString();
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error('Failed to fetch job vacancies');
    }
    const vacancies = await response.json();
    displayVacancies(vacancies);
}

document.getElementById('search-button').addEventListener('click', searchVacancies);

window.onload = fetchJobVacancies;
