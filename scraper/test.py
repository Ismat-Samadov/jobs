# import requests
# from bs4 import BeautifulSoup
#
#
# def scrape_bank_of_baku_jobs():
#     print("Scraping started for bank of baku")
#     url = "https://careers.bankofbaku.com/az/vacancies"
#     response = requests.get(url, verify=False)  # Disabling SSL verification
#     soup = BeautifulSoup(response.text, 'html.parser')
#
#     jobs = []
#     job_cards = soup.find_all('div', class_='vacancy-list-block')
#
#     for job_card in job_cards:
#         title = job_card.find('div', class_='vacancy-list-block-header').get_text(strip=True)
#         department = job_card.find_all('label')[0].get_text(strip=True) if job_card.find_all(
#             'label') else 'No department listed'
#         location = job_card.find_all('label')[1].get_text(strip=True) if len(
#             job_card.find_all('label')) > 1 else 'No location listed'
#         deadline = job_card.find('label', class_='light-red-bg').get_text(strip=True) if job_card.find('label',
#                                                                                                        class_='light-red-bg') else 'No deadline listed'
#
#         jobs.append({
#             'title': title,
#             'department': department,
#             'location': location,
#             'deadline': deadline
#         })
#     print("scraping completed for bank of baku")
#     return jobs
#
#
# # Example usage
# job_listings = scrape_bank_of_baku_jobs()
# for job in job_listings:
#     print(job)
import pandas as pd
import requests
from bs4 import BeautifulSoup


def ishelanlari_az():
    print("Scraping started for ishelanlari.az")
    url = "https://ishelanlari.az/az/vacancies//0/360/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            jobs = []
            for job in soup.find_all("div", class_="card-body"):
                title_element = job.find("h2", class_="font-weight-bold")
                company_element = job.find("a", class_="text-muted")
                details_link_element = job.find("a", class_="position-absolute")

                title = title_element.text.strip() if title_element else "No title provided"
                company = company_element.text.strip() if company_element else "No company provided"
                link = details_link_element["href"] if details_link_element else "No link provided"

                jobs.append({
                    "company": company,
                    "vacancy": title,
                    "link": "https://ishelanlari.az" + link
                })
            print("Scraping completed for ishelanlari.az")
            return pd.DataFrame(jobs)
        else:
            print(f"Failed to retrieve data, status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")


# Example usage
jobs_data = ishelanlari_az()
print(jobs_data)
