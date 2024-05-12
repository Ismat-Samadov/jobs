import streamlit as st
import requests
import datetime

API_BASE_URL = "https://job-api-cv1f.onrender.com/data/"

# Set page config with new favicon
st.set_page_config(
    page_title='JOBS',
    page_icon='path_to_your_favicon/favicon.ico',  # Update the path to where your favicon file is located
    layout='wide',
    initial_sidebar_state='expanded'
)

def fetch_data(endpoint, params=None):
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json(), None
    except requests.HTTPError as http_error:
        return None, str(http_error)
    except Exception as err:
        return None, str(err)


def display_data(data):
    if data:
        for item in data:
            company = item.get('company', 'Unknown Company')
            position = item.get('vacancy', 'Unknown Position')
            apply_link = item.get('apply_link', '#')
            scrape_date_raw = item.get('scrape_date', 'No date available')
            first_letter = company[0] if company else 'U'  # Default to 'U' for unknown

            # Parse and format the date
            try:
                parsed_date = datetime.datetime.fromisoformat(
                    scrape_date_raw[:-1])  # Remove the last character if it's 'Z'
                scrape_date = parsed_date.strftime('%B %d, %Y at %H:%M:%S')
            except ValueError:
                scrape_date = scrape_date_raw  # Use the original string if parsing fails

            # image_url = f"https://via.placeholder.com/100/0000FF/FFFFFF?text={first_letter}"
            # image_url = f"https://via.placeholder.com/100/800080/FFFFFF?text={first_letter}"
            image_url = f"https://via.placeholder.com/100/FFA500/FFFFFF?text={first_letter}"

            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image(image_url, width=100)  # Display the first letter of the company name as an image
                with col2:
                    st.subheader(f"{company} - {position}")
                    st.caption(f"Scrape Date: {scrape_date}")
                    st.markdown(f"[Apply Here]({apply_link})", unsafe_allow_html=True)
    else:
        st.error("No data available for the given query.")


def main():
    st.title("Advanced Job Vacancies Search")

    # Search form at the top
    with st.form("search_form"):
        company = st.text_input("Company Name", key='company').strip()
        position = st.text_input("Position", key='position').strip()
        search = st.form_submit_button("Search")

    # Pagination controls
    page = st.number_input("Page Number", value=1, min_value=1, key='page_number')
    page_size = st.selectbox("Results per page", options=[10, 20, 50], index=0, key='page_size')
    fetch_data_button = st.button("Fetch Data", key='fetch_data_button')

    # Data fetching logic
    if search or fetch_data_button:
        # If user performs a search or changes pagination
        with st.spinner("Fetching data..."):
            query_params = {"page": page, "page_size": page_size}
            if company:
                query_params["company"] = company
            if position:
                query_params["position"] = position
            data, error = fetch_data("", query_params)
            if error:
                st.error(f"Failed to fetch data: {error}")
            else:
                display_data(data)
    else:
        # Initial data loading when the app is first opened
        with st.spinner("Loading initial data..."):
            initial_data, initial_error = fetch_data("", {"page": 1, "page_size": 10})
            if initial_error:
                st.error(f"Failed to fetch initial data: {initial_error}")
            else:
                display_data(initial_data)


if __name__ == "__main__":
    main()
