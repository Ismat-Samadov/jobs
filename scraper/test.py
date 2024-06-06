import requests
from bs4 import BeautifulSoup

def scrape_job_vacancies(page_url):
    response = requests.get(page_url)
    if response.status_code != 200:
        print("Failed to retrieve the page")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    vacancies = []

    events = soup.find_all('div', class_='event')
    for event in events:
        title_tag = event.find('a', class_='event__link')
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag['href']
            deadline_tag = event.find('span', class_='event__time')
            deadline = deadline_tag.get_text(strip=True) if deadline_tag else 'N/A'
            vacancies.append({'title': title, 'link': link, 'deadline': deadline})

    return vacancies

page_url = "https://its.gov.az/page/vakansiyalar?page=6"
vacancies = scrape_job_vacancies(page_url)
for vacancy in vacancies:
    print(f"Title: {vacancy['title']}")
    print(f"Link: {vacancy['link']}")
    print(f"Deadline: {vacancy['deadline']}")
    print("-" * 40)
