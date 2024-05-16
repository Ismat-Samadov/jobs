import requests
from bs4 import BeautifulSoup

def scrape_bank_of_baku_jobs():
    print("Scraping started for Bank of Baku")
    url = "https://careers.bankofbaku.com/az/vacancies"
    response = requests.get(url, verify=False)  # Disabling SSL verification for the sake of the example
    soup = BeautifulSoup(response.text, 'html.parser')

    jobs = []
    job_blocks = soup.find_all('div', class_='main-cell mc-50p')

    for job_block in job_blocks:
        link_tag = job_block.find('a')
        if link_tag:
            link = 'https://careers.bankofbaku.com' + link_tag['href']
            job_info = job_block.find('div', class_='vacancy-list-block-content')
            title = job_info.find('div', class_='vacancy-list-block-header').get_text(strip=True) if job_info else 'No title provided'
            department_label = job_info.find('label', class_='light-red-bg')
            deadline = department_label.get_text(strip=True) if department_label else 'No deadline listed'
            department_info = job_info.find_all('label')[0].get_text(strip=True) if len(job_info.find_all('label')) > 0 else 'No department listed'
            location_info = job_info.find_all('label')[1].get_text(strip=True) if len(job_info.find_all('label')) > 1 else 'No location listed'

            jobs.append({
                'company':'Bank of Baku',
                'vacancy': title,
                'apply_link': link
            })

    print("Scraping completed for Bank of Baku")
    return jobs

# Example usage
job_listings = scrape_bank_of_baku_jobs()
for job in job_listings:
    print(job)
