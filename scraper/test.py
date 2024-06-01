import requests
from bs4 import BeautifulSoup

# URL of the job listings page
url = 'https://jobbox.az/az/vacancies?page=3'

# Send a GET request to the URL
response = requests.get(url)
response.raise_for_status()  # Ensure we got a successful response

# Parse the HTML content of the page
soup = BeautifulSoup(response.text, 'html.parser')

# Find all job listing items
job_items = soup.find_all('li', class_='item')

# Iterate over each job item and extract the details
jobs = []
for item in job_items:
    job = {}

    link_tag = item.find('a')
    if link_tag:
        job['link'] = link_tag['href']
    else:
        continue  # Skip if no link found

    title_ul = item.find('ul', class_='title')
    if title_ul:
        title_div = title_ul.find_all('li')
        job['title'] = title_div[0].text.strip() if len(title_div) > 0 else None
        job['salary'] = title_div[1].text.strip() if len(title_div) > 1 else None
    else:
        continue  # Skip if title information is missing

    address_ul = item.find('ul', class_='address')
    if address_ul:
        address_div = address_ul.find_all('li')
        job['company'] = address_div[0].text.strip() if len(address_div) > 0 else None
        job['location'] = address_div[1].text.strip() if len(address_div) > 1 else None
    else:
        continue  # Skip if address information is missing

    description_ul = item.find('ul', class_='desc')
    if description_ul:
        description_div = description_ul.find_all('li')
        job['description'] = ' '.join([desc.text.strip() for desc in description_div if desc.text.strip()])
    else:
        job['description'] = None

    jobs.append(job)

# Print the extracted job details
for job in jobs:
    print(f"Title: {job['title']}")
    print(f"Salary: {job['salary']}")
    print(f"Company: {job['company']}")
    print(f"Location: {job['location']}")
    print(f"Description: {job['description']}")
    print(f"Link: {job['link']}")
    print('-' * 40)
