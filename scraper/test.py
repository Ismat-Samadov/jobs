import requests

def scrape_vakansiya_biz_vacancies(url, params):
  """Scrapes vacancies from vakansiya.biz API.

  Args:
      url (str): The base URL of the API endpoint.
      params (dict): A dictionary containing query parameters.

  Returns:
      list: A list of dictionaries, where each dictionary represents a vacancy.

  Raises:
      requests.exceptions.RequestException: If an error occurs during the API request.
  """

  try:
      response = requests.get(url, params=params)
      response.raise_for_status()  # Raise an exception for non-2xx status codes
      data = response.json()

      if 'data' in data and data['data']:
          vacancies = data['data']  # Extract vacancies from successful response
          if len(vacancies) != 20:  # Check for expected vacancy count (adjust number if needed)
              print("Warning: Expected 20 vacancies, but only fetched", len(vacancies))
          return vacancies
      else:
          print("Warning: No vacancies found in the response.")
          return []  # Return empty list if no vacancies found
  except requests.exceptions.RequestException as e:
      print(f"Error scraping vacancies: {e}")
      return []  # Return empty list on error

# Example usage
base_url = "https://api.vakansiya.biz/api/v1/vacancies/search"
params = {
  "page": 15,
  "country_id": 108,  # Adjust country ID (Azerbaijan)
  "city_id": 0,  # All cities (optional)
  "industry_id": 0,  # All industries (optional)
  # Add other parameters as needed (job type, work type, etc.)
}

vacancies = scrape_vakansiya_biz_vacancies(base_url, params)

if vacancies:
  for vacancy in vacancies:
      # Process each vacancy dictionary here
      print(f"Job Title: {vacancy.get('title')}")
      print(f"Company: {vacancy.get('company_name')}")
      # Extract and print other relevant details from the vacancy dictionary
else:
  print("No vacancies found for the given criteria.")
