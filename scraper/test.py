import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_jobs(base_url, start_page=1, end_page=20):
    all_jobs = []
    for page in range(start_page, end_page + 1):
        url = f"{base_url}/page-{page}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers)
        print(f"URL: {url} - Status Code: {response.status_code}")  # Debugging line
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            job_tables = soup.find_all('table', class_='background')
            for job in job_tables:
                title_link = job.find('a', href=True)
                salary = job.find('div', class_='salary').text if job.find('div', class_='salary') else 'No salary listed'
                company = job.find('div', class_='company').text if job.find('div', class_='company') else 'No company listed'
                description = job.find('div', class_='description').text if job.find('div', class_='description') else 'No description'
                all_jobs.append({
                    'Title': title_link.text.strip(),
                    'Company': company,
                    'Salary': salary,
                    'Description': description,
                    'Link': 'https://ejob.az' + title_link['href']
                })
        else:
            print(f"Failed to retrieve page: {page} - Response: {response.text[:500]}")  # Print first 500 characters of the response body
    return pd.DataFrame(all_jobs)

# Example usage
base_url = 'https://ejob.az/is-elanlari'
jobs_df = scrape_jobs(base_url)  # Automatically scrapes pages 1 to 20
print(jobs_df)