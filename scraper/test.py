import requests
from bs4 import BeautifulSoup


def scrape_bank_of_baku_jobs():
    print("Scraping started for bank of baku")
    url = "https://careers.bankofbaku.com/az/vacancies"
    response = requests.get(url, verify=False)  # Disabling SSL verification
    soup = BeautifulSoup(response.text, 'html.parser')

    jobs = []
    job_cards = soup.find_all('div', class_='vacancy-list-block')

    for job_card in job_cards:
        title = job_card.find('div', class_='vacancy-list-block-header').get_text(strip=True)
        department = job_card.find_all('label')[0].get_text(strip=True) if job_card.find_all(
            'label') else 'No department listed'
        location = job_card.find_all('label')[1].get_text(strip=True) if len(
            job_card.find_all('label')) > 1 else 'No location listed'
        deadline = job_card.find('label', class_='light-red-bg').get_text(strip=True) if job_card.find('label',
                                                                                                       class_='light-red-bg') else 'No deadline listed'

        jobs.append({
            'title': title,
            'department': department,
            'location': location,
            'deadline': deadline
        })
    print("scraping completed for bank of baku")
    return jobs


# Example usage
job_listings = scrape_bank_of_baku_jobs()
for job in job_listings:
    print(job)