import requests


def fetch_vacancies(pages=10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
        'Accept': 'application/json',
        'Referer': 'https://careers.abb-bank.az/vakansiyalar',
        'X-Csrf-Token': 'J4xdXYEeZ5030GVkC33GhjHiFxpwftTEl8llnP1h',
        'X-Requested-With': 'XMLHttpRequest',
        'Dnt': '1'
    }
    all_vacancies = []
    for page in range(1, pages + 1):
        url = f"https://careers.abb-bank.az/api/vacancy/v2/get?page={page}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            vacancies_on_page = data.get('data', [])
            all_vacancies.extend(vacancies_on_page)
        else:
            print(f"Failed to fetch data from page {page}. Status code: {response.status_code}")

    return all_vacancies


# Example usage:
all_vacancies = fetch_vacancies(pages=10)
for vacancy in all_vacancies:
    print(vacancy['title'])
