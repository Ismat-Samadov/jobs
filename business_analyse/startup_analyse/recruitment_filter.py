import pandas as pd

# Load the dataset
file_path = 'scraped_data.csv'
data = pd.read_csv(file_path)

# Remove rows with placeholder data ('.')
cleaned_data = data[data.iloc[:, 0] != '.']

# Define keywords related to job listing and employee hire platforms
keywords = [
    "job listing", "employee hire", "recruitment", "job platform", "hiring", 
    "employment", "career portal", "job board", "talent acquisition", "job search", 
    "job vacancy", "staffing", "HR platform", "employment platform", "recruitment platform"
]

# Search for these keywords in the description columns
description_column = 'Please Describe your idea in 1 short paragraph (100-150 words)'

# Filter rows that contain any of the keywords in the description
filtered_data = cleaned_data[cleaned_data[description_column].str.contains('|'.join(keywords), case=False, na=False)]

# Display more filtered ideas
filtered_ideas = filtered_data[[description_column]]
print(filtered_ideas)
# Save the filtered ideas to a CSV file with all columns
output_filtered_path = "recruitment_filter.csv"
filtered_data.to_csv(output_filtered_path, index=False)

output_filtered_path
