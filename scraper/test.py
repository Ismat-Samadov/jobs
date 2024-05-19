import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_banker_az(base_url, num_pages=10):
    all_job_titles = []
    all_company_names = []
    all_apply_links = []

    for page in range(1, num_pages + 1):
        url = f"{base_url}/page/{page}/"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        job_listings = soup.find_all('div', class_='list-data')

        job_titles = []
        company_names = []
        apply_links = []

        for job in job_listings:
            # Extract job title and link
            job_info = job.find('div', class_='job-info')
            title_tag = job_info.find('a') if job_info else None
            title = title_tag.text.strip() if title_tag else None
            link = title_tag['href'] if title_tag else None

            # Extract company name from the alt attribute of the img tag within the company logo
            company_logo = job.find('div', class_='company-logo')
            company_img = company_logo.find('img') if company_logo else None
            company = company_img.get('alt') if company_img else None

            # Split the title and company if they are together
            if title and '-' in title:
                title_parts = title.split(' – ')
                title = title_parts[0].strip()
                if len(title_parts) > 1:
                    company = title_parts[1].strip()

            if title and company and link:
                job_titles.append(title)
                company_names.append(company)
                apply_links.append(link)

        all_job_titles.extend(job_titles)
        all_company_names.extend(company_names)
        all_apply_links.extend(apply_links)

    df = pd.DataFrame({
        'company': all_company_names,
        'vacancy': all_job_titles,
        'apply_link': all_apply_links
    })

    return df

# Example usage
base_url = 'https://banker.az/vakansiyalar'
scraped_data = scrape_banker_az(base_url)
print(scraped_data.head())
