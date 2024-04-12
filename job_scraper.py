import requests
from bs4 import BeautifulSoup

# Send a GET request to the job listing page
url = 'https://example.com/jobs'
response = requests.get(url)

# Parse HTML content
soup = BeautifulSoup(response.text, 'html.parser')

# Extract job information
job_listings = []
for job in soup.find_all('div', class_='job'):
    title = job.find('h2').text.strip()
    company = job.find('p', class_='company').text.strip()
    location = job.find('p', class_='location').text.strip()
    description = job.find('div', class_='description').text.strip()
    job_listings.append({'title': title, 'company': company, 'location': location, 'description': description})

# Print scraped job data
print(job_listings)
