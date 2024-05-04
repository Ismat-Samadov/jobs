//app.js


// Initialize Google Sign-In
function initGoogleSignIn() {
    gapi.load('auth2', function () {
        gapi.auth2.init({
            client_id: 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com'
        }).then(() => {
            // Render the Google Sign-In button
            gapi.signin2.render('google-signin-button', {
                scope: 'email profile',
                width: 200,
                height: 40,
                longtitle: true,
                theme: 'dark',
                onsuccess: onGoogleSignInSuccess,
                onfailure: onGoogleSignInFailure
            });
        }).catch((error) => {
            console.error('Error initializing Google Sign-In:', error);
        });
    });
}

// Handle successful Google sign-in
function onGoogleSignInSuccess(googleUser) {
    const profile = googleUser.getBasicProfile();
    const idToken = googleUser.getAuthResponse().id_token;

    // Send the ID token to your backend server for verification and authentication
    // Example:
    // fetch('/your-backend-endpoint', {
    //   method: 'POST',
    //   headers: {
    //     'Content-Type': 'application/json'
    //   },
    //   body: JSON.stringify({ idToken })
    // })
    // .then(response => response.json())
    // .then(data => {
    //   // Handle server response
    // })
    // .catch(error => {
    //   console.error('Error:', error);
    // });

    console.log('Google Sign-In successful!');
    console.log('ID token:', idToken);
}

// Handle failed Google sign-in
function onGoogleSignInFailure(error) {
    console.error('Google Sign-In failed:', error);
}

// Load Google Sign-In
window.onload = function () {
    gapi.load('auth2', initGoogleSignIn);
};

let currentPage = 1; // Track the current page number

document.getElementById('prev-page').addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        fetchJobVacancies();
    }
});

document.getElementById('next-page').addEventListener('click', () => {
    currentPage++;
    fetchJobVacancies();
});

async function fetchJobVacancies() {
    try {
        const response = await fetch(`https://job-api-cv1f.onrender.com/data/?page=${currentPage}`);
        if (!response.ok) {
            throw new Error('Failed to fetch job vacancies');
        }
        const vacancies = await response.json();
        displayVacancies(vacancies);
    } catch (error) {
        console.error('Error fetching job vacancies:', error.message);
    }
}

// Update displayVacancies function to include pagination logic
function displayVacancies(vacancies) {
    const vacancyList = document.getElementById('vacancy-list');
    vacancyList.innerHTML = '';
    vacancies.forEach(vacancy => {
        // Render each vacancy item as before
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

    // Update pagination controls
    document.getElementById('page-number').value = currentPage;
}

// Event listener for the page number input field
document.getElementById('page-number').addEventListener('change', () => {
    const pageNumber = parseInt(document.getElementById('page-number').value);
    if (!isNaN(pageNumber) && pageNumber >= 1) {
        currentPage = pageNumber;
        fetchJobVacancies();
    } else {
        alert('Please enter a valid page number.');
    }
});

// Async function to search for vacancies
async function searchVacancies() {
    const searchInputCompany = document.getElementById('search-input-company').value;
    const searchInputPosition = document.getElementById('search-input-position').value;

    // Construct the base URL
    let url = 'https://job-api-cv1f.onrender.com/data/?';

    // Add company parameter if it's provided
    if (searchInputCompany) {
        url += `company=${encodeURIComponent(searchInputCompany)}&`;
    }

    // Add position parameter if it's provided
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

// Event listener for the search button
document.getElementById('search-button').addEventListener('click', searchVacancies);

// Initialize the page with job vacancies
window.onload = function () {
    fetchJobVacancies();
    toggleMode(); // Initially toggle mode to set the default mode
};

// Function to toggle between light and dark modes
function toggleMode() {
    const body = document.body;
    body.classList.toggle('light-mode'); // Toggle light mode
    body.classList.toggle('dark-mode'); // Toggle dark mode
}

// Event listener for mode toggle button
document.getElementById('toggle-mode-button').addEventListener('click', toggleMode);
