# import streamlit as st
# import requests
# import datetime
#
# API_BASE_URL = "https://job-api-cv1f.onrender.com/data/"
#
# # Set page config with new favicon
# st.set_page_config(
#     page_title='JOBS',
#     page_icon='frontend/assets/favicon.ico',
#     layout='centered',
#     initial_sidebar_state='expanded'
# )
#
# def hide_streamlit_style():
#     hide_footer_style = """
#         <style>
#         #MainMenu {visibility: hidden;}
#         footer {visibility: hidden;}
#         </style>
#     """
#     st.markdown(hide_footer_style, unsafe_allow_html=True)
#
# def fetch_data(endpoint, params=None):
#     try:
#         response = requests.get(f"{API_BASE_URL}{endpoint}", params=params)
#         response.raise_for_status()
#         return response.json(), None
#     except requests.HTTPError as http_error:
#         return None, str(http_error)
#     except Exception as err:
#         return None, str(err)
#
# def display_data(data):
#     if data:
#         for item in data:
#             company = item.get('company', 'Unknown Company')
#             position = item.get('vacancy', 'Unknown Position')
#             apply_link = item.get('apply_link', '#')
#             scrape_date_raw = item.get('scrape_date', 'No date available')
#             first_letter = company[0] if company else 'U'
#             try:
#                 parsed_date = datetime.datetime.fromisoformat(scrape_date_raw[:-1])
#                 scrape_date = parsed_date.strftime('%B %d, %Y at %H:%M:%S')
#             except ValueError:
#                 scrape_date = scrape_date_raw
#
#             image_url = f"https://via.placeholder.com/100/FFA500/FFFFFF?text={first_letter}"
#
#             with st.container():
#                 col1, col2 = st.columns([1, 4])
#                 with col1:
#                     st.image(image_url, width=100)
#                 with col2:
#                     st.subheader(f"{company} - {position}")
#                     st.caption(f"Scrape Date: {scrape_date}")
#                     st.markdown(f"[Apply Here]({apply_link})", unsafe_allow_html=True)
#     else:
#         st.error("No data available for the given query.")
#
# def main():
#     hide_streamlit_style()
#     st.title("Job Search")
#
#     with st.form("search_form"):
#         company = st.text_input("Company Name", key='company').strip()
#         position = st.text_input("Position", key='position').strip()
#         search = st.form_submit_button("Search")
#
#     page = st.number_input("Page Number", value=1, min_value=1, key='page_number')
#     page_size = st.selectbox("Results per page", options=[10, 20, 50], index=0, key='page_size')
#     fetch_data_button = st.button("Fetch Data", key='fetch_data_button')
#
#     if search or fetch_data_button:
#         with st.spinner("Fetching data..."):
#             query_params = {"page": page, "page_size": page_size}
#             if company:
#                 query_params["company"] = company
#             if position:
#                 query_params["position"] = position
#             data, error = fetch_data("", query_params)
#             if error:
#                 st.error(f"Failed to fetch data: {error}")
#             else:
#                 display_data(data)
#     else:
#         with st.spinner("Loading initial data..."):
#             initial_data, initial_error = fetch_data("", {"page": 1, "page_size": 10})
#             if initial_error:
#                 st.error(f"Failed to fetch initial data: {initial_error}")
#             else:
#                 display_data(initial_data)
#
# if __name__ == "__main__":
#     main()

import streamlit as st
import requests
import datetime

API_BASE_URL = "https://job-api-cv1f.onrender.com/data/"

# Set page config with custom favicon
st.set_page_config(
    page_title='JOBS',
    page_icon='frontend/assets/favicon.ico',  # Ensure the path to favicon is correct
    layout='wide',
    initial_sidebar_state='expanded'
)

def hide_streamlit_style():
    """Hide default Streamlit style settings."""
    hide_footer_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .css-18e3th9 {background-color: #f0f0f0;}
        </style>
    """
    st.markdown(hide_footer_style, unsafe_allow_html=True)

def fetch_data(endpoint, params=None):
    """Fetch data from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json(), None
    except requests.HTTPError as http_error:
        return None, str(http_error)
    except Exception as err:
        return None, str(err)

def display_data(data):
    """Display data in a formatted way."""
    if data:
        for item in data:
            company = item.get('company', 'Unknown Company')
            position = item.get('vacancy', 'Unknown Position')
            apply_link = item.get('apply_link', '#')
            scrape_date_raw = item.get('scrape_date', 'No date available')
            first_letter = company[0] if company else 'U'

            try:
                parsed_date = datetime.datetime.fromisoformat(scrape_date_raw[:-1])
                scrape_date = parsed_date.strftime('%B %d, %Y at %H:%M:%S')
            except ValueError:
                scrape_date = scrape_date_raw

            image_url = f"https://via.placeholder.com/100/FFA500/FFFFFF?text={first_letter}"

            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image(image_url, width=100)  # Display dynamic image based on company's first letter
                with col2:
                    st.subheader(f"{company} - {position}")
                    st.caption(f"Scrape Date: {scrape_date}")
                    st.markdown(f"[Apply Here]({apply_link})", unsafe_allow_html=True)
    else:
        st.error("No data available for the given query.")

def main():
    """Main function to render the Streamlit app."""
    hide_streamlit_style()
    st.title("Job Search")
    st.sidebar.header("Search Filters")

    with st.sidebar.form("search_form"):
        company = st.text_input("Company Name").strip()
        position = st.text_input("Position").strip()
        page = st.number_input("Page Number", value=1, min_value=1)
        page_size = st.selectbox("Results per page", options=[10, 20, 50], index=0)
        search = st.form_submit_button("Search")

    if search:
        with st.spinner("Fetching data..."):
            query_params = {"company": company, "position": position, "page": page, "page_size": page_size}
            data, error = fetch_data("", query_params)
            if error:
                st.error(f"Failed to fetch data: {error}")
            else:
                display_data(data)

if __name__ == "__main__":
    main()
