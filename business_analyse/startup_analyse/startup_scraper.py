import requests
import pandas as pd

# Base API URL
base_api_url = "https://api.rready.com/PASHAHolding/ticket/kickbox/PASHAHolding-kickbox-"

# Headers for the API requests
headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6",
    "App-Id": "app",
    "Authorization": "Bearer eyJraWQiOiIxIiwiYWxnIjoiRWREU0EifQ.eyJpc3MiOiJraWNrYm94LWltcHJvdmUiLCJzdWIiOiJhNjE0ZWZjOC0zMmI4LTRjYjItYjgwYi1iYzRiZDAxOGVkOWQiLCJhdWQiOiJQQVNIQUhvbGRpbmciLCJjb250ZXh0cyI6WyJQQVNIQUhvbGRpbmciXSwiZXhwIjoxNzIwOTczMDIxfQ.dAMo2ShCi3rArfI_Pbr0LFJoNfnQDW-0OThJbAormeCqgnWjMvI8ok6zhtMFMfoWPaGtTVKxUIjOKqvprBIIAQ",
    "Content-Type": "application/json",
    "Dnt": "1",
    "Origin": "https://app.rready.com",
    "Referer": "https://app.rready.com/",
    "Sec-Ch-Ua": "\"Not/A)Brand\";v=\"8\", \"Chromium\";v=\"126\", \"Google Chrome\";v=\"126\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "\"macOS\"",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

# Initialize an empty list to store all the records
all_records = []

# Loop through the range of IDs
for i in range(1, 1500):
    api_url = f"{base_api_url}{i}"
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()

        # Flatten the JSON data for easy DataFrame creation
        flattened_data = {
            "Tagline": data.get("meta", {}).get("tagline", "."),
            "LinkedIn Profile URL": data.get("meta", {}).get("linkedin", "."),
            "Please Describe your idea in 1 short paragraph (100-150 words)": data.get("meta", {}).get("description", "."),
            "What Problem(s) does your project solve? (give in bullet points)": data.get("meta", {}).get("problemdescription", "."),
            "Summarize the business model in a few sentences. How do you make money?": data.get("meta", {}).get("businessmodeldescription", "."),
            "Why did you pick this idea to work on? What is motivating you to solve this problem? (150 words minimum)": data.get("meta", {}).get("motivationdescription", "."),
            "How will your idea bring synergetic impact and create value within the PASHA Group? Please describe in 100 words": data.get("meta", {}).get("synergydescription", "."),
            "What is your unique value proposition? What's new about what you're doing? How different are you from your competitors?": data.get("meta", {}).get("valuepropdescription", "."),
            "Please share any previous experiences or skills that demonstrate your ability to lead and drive innovation?": data.get("meta", {}).get("experiencedescription", "."),
            "Who do you think will be sponsoring your idea?": "Pasha Holding" if data.get("meta", {}).get("sponsoringpasha") else ".",
            "Required skills": ", ".join(data.get("skills", [])),
            "I want to receive newsletter from Innovation Team to get the latest news about the KICKBOX program": "Yes" if data.get("meta", {}).get("newsletterpasha") else ".",
            "Intrapreneurship is not easy. It will require you to attend weekly workshops and coaching sessions. In addition, for every week you will need to do homework in order to be able to successfully validate your ideas in the Redbox stage. Please confirm whether you will be able to commit your time to your idea.": "Yes, I do confirm" if data.get("meta", {}).get("intrapreneurshipcomittment") else "."
        }

        # Append the flattened data to the records list
        all_records.append(flattened_data)
    else:
        print(f"Failed to retrieve data for ID {i}: {response.status_code}")

# Convert the list of records to a DataFrame
df = pd.DataFrame(all_records)

# Save the DataFrame to a CSV file
csv_file_path = "scraped_data.csv"
df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')

print(f"Data saved to {csv_file_path}")
