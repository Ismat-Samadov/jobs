import requests

class JobScraper:
    def __init__(self):
        self.base_url = "https://api.vakansiya.biz/api/v1/vacancies/search"
        self.headers = {
            'Content-Type': 'application/json'
        }

    def parse_vakansiya_biz(self):
        page = 1
        all_jobs = []

        while True:
            response = requests.get(f"{self.base_url}?page={page}&country_id=108&city_id=0&industry_id=0&job_type_id=0&work_type_id=0&gender=-1&education_id=0&experience_id=0&min_salary=0&max_salary=0&title=", headers=self.headers)

            if response.status_code != 200:
                print(f"Failed to fetch page {page}: {response.status_code}")
                break

            data = response.json()
            jobs = data.get('data', [])
            all_jobs.extend(jobs)

            if not data.get('next_page_url'):
                break

            page += 1

        return all_jobs

# Creating an instance of the JobScraper class
scraper = JobScraper()

# Calling the parse_vakansiya_biz method on the instance
data = scraper.parse_vakansiya_biz()
print(data)
