# import streamlit as st
# import requests
# import datetime
#
# API_BASE_URL = "https://job-api-cv1f.onrender.com/data/"
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
# # def display_data(data):
# #     if data:
# #         for item in data:
# #             company = item.get('company', 'Unknown Company')
# #             position = item.get('vacancy', 'Unknown Position')
# #             description = item.get('description', 'No description available')[:100]
# #             apply_link = item.get('apply_link', '#')
# #             scrape_date = item.get('scrape_date', 'No date available')
# #
# #             st.subheader(f"{company} - {position}")
# #             st.write(f"Scrape Date: {scrape_date}")
# #             st.markdown(f"[Apply Here]({apply_link})", unsafe_allow_html=True)
# #     else:
# #         st.error("No data available for the given query.")
#
#
#
#
# def display_data(data):
#     if data:
#         for item in data:
#             company = item.get('company', 'Unknown Company')
#             position = item.get('vacancy', 'Unknown Position')
#             description = item.get('description', 'No description available')[:100]
#             apply_link = item.get('apply_link', '#')
#             scrape_date_raw = item.get('scrape_date', 'No date available')
#
#             # Parse and format the date
#             try:
#                 parsed_date = datetime.datetime.fromisoformat(
#                     scrape_date_raw[:-1])  # Remove the last character if it's 'Z'
#                 scrape_date = parsed_date.strftime('%B %d, %Y at %H:%M:%S')
#             except ValueError:
#                 scrape_date = scrape_date_raw  # Use the original string if parsing fails
#
#             st.subheader(f"{company} - {position}")
#             st.write(f"Scrape Date: {scrape_date}")
#             st.markdown(f"[Apply Here]({apply_link})", unsafe_allow_html=True)
#     else:
#         st.error("No data available for the given query.")
#
#
# def main():
#     st.title("Advanced Job Vacancies Search")
#
#     # Fetch and display initial set of job vacancies when the page first loads
#     initial_data, initial_error = fetch_data("", {"page": 1, "page_size": 10})  # Default page and size
#     if initial_error:
#         st.error(f"Failed to fetch initial data: {initial_error}")
#     elif initial_data:
#         display_data(initial_data)
#
#     with st.form("search_form"):
#         company = st.text_input("Company Name").strip()
#         position = st.text_input("Position").strip()
#         search = st.form_submit_button("Search")
#
#         if search and (company or position):
#             with st.spinner("Fetching data..."):
#                 data, error = fetch_data("", {"company": company, "position": position})
#                 if error:
#                     st.error(f"Failed to fetch data: {error}")
#                 else:
#                     display_data(data)
#
#     with st.expander("Advanced Search Options"):
#         page = st.number_input("Page Number", value=1, min_value=1)
#         page_size = st.selectbox("Results per page", options=[10, 20, 50], index=0)
#         fetch = st.button("Fetch Data")
#
#         if fetch:
#             with st.spinner("Fetching data..."):
#                 data, error = fetch_data("", {"page": page, "page_size": page_size})
#                 if error:
#                     st.error(f"Failed to fetch data: {error}")
#                 else:
#                     display_data(data)
#
# if __name__ == "__main__":
#     main()
import streamlit as st
import requests
import datetime

API_BASE_URL = "https://job-api-cv1f.onrender.com/data/"

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

            # Parse and format the date
            try:
                parsed_date = datetime.datetime.fromisoformat(scrape_date_raw[:-1])
                scrape_date = parsed_date.strftime('%B %d, %Y at %H:%M:%S')
            except ValueError:
                scrape_date = scrape_date_raw  # Use the original string if parsing fails

            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image("https://via.placeholder.com/100", width=100)  # Placeholder for company logo
                with col2:
                    st.subheader(f"{company} - {position}")
                    st.caption(f"Scrape Date: {scrape_date}")
                    st.markdown(f"[Apply Here]({apply_link})", unsafe_allow_html=True)
    else:
        st.error("No data available for the given query.")

def main():
    st.title("Advanced Job Vacancies Search")

    # Fetch and display initial set of job vacancies when the page first loads
    initial_data, initial_error = fetch_data("", {"page": 1, "page_size": 10})  # Default page and size
    if initial_error:
        st.error(f"Failed to fetch initial data: {initial_error}")
    elif initial_data:
        display_data(initial_data)

    with st.form("search_form"):
        company = st.text_input("Company Name").strip()
        position = st.text_input("Position").strip()
        search = st.form_submit_button("Search")

        if search and (company or position):
            with st.spinner("Fetching data..."):
                data, error = fetch_data("", {"company": company, "position": position})
                if error:
                    st.error(f"Failed to fetch data: {error}")
                else:
                    display_data(data)

    with st.expander("Advanced Search Options"):
        page = st.number_input("Page Number", value=1, min_value=1)
        page_size = st.selectbox("Results per page", options=[10, 20, 50], index=0)
        fetch = st.button("Fetch Data")

        if fetch:
            with st.spinner("Fetching data..."):
                data, error = fetch_data("", {"page": page, "page_size": page_size})
                if error:
                    st.error(f"Failed to fetch data: {error}")
                else:
                    display_data(data)

if __name__ == "__main__":
    main()
