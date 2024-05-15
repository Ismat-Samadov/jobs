import pandas as pd
import requests
from bs4 import BeautifulSoup


def vakansiya_az():
    url = 'https://www.vakansiya.az/az/'
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve page with status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')

    jobs = []

    job_divs = soup.find_all('div', id='js-jobs-wrapper')
    print(f"Found {len(job_divs)} job postings.")

    for job_div in job_divs:
        job = {}
        company = job_div.find_all('div', class_='js-fields')[1].find('a')
        title = job_div.find('a', class_='jobtitle')
        apply_link = title['href'] if title else None

        job['company'] = company.get_text(strip=True) if company else 'N/A'
        job['vacancy'] = title.get_text(strip=True) if title else 'N/A'
        job['apply_link'] = 'https://www.vakansiya.az' + apply_link if apply_link else 'N/A'
        print(f"Job found: {job}")
        jobs.append(job)

    return pd.DataFrame(jobs)

print(vakansiya_az())