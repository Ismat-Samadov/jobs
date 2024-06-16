import matplotlib.pyplot as plt
from wordcloud import WordCloud
from fpdf import FPDF
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import Counter

# Load the dataset
file_path = 'startups.csv'
startups_df = pd.read_csv(file_path)

# Initial preprocessing
placeholders = ['.', ' ', 'null', 'N/A', 'na', 'NaN', '']
for placeholder in placeholders:
    startups_df.replace(placeholder, np.nan, inplace=True)

# Fill NaN values with empty strings for the description column
startups_df['Please Describe your idea in 1 short paragraph (100-150 words)'].fillna('', inplace=True)

# Extract the descriptions
descriptions = startups_df['Please Describe your idea in 1 short paragraph (100-150 words)']

# Vectorize the descriptions using TF-IDF
vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
X = vectorizer.fit_transform(descriptions)

# Apply KMeans clustering to group descriptions into categories
n_clusters = 5
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
kmeans.fit(X)

# Assign cluster labels to the startups
startups_df['Category'] = kmeans.labels_

# Improved preprocessing by filtering out completely empty descriptions
filtered_descriptions = descriptions[descriptions.str.strip() != '']

# Re-vectorize the descriptions using TF-IDF
X_filtered = vectorizer.fit_transform(filtered_descriptions)

# Re-apply KMeans clustering to group descriptions into categories
kmeans_filtered = KMeans(n_clusters=n_clusters, random_state=42)
kmeans_filtered.fit(X_filtered)

# Create a new DataFrame for the filtered descriptions and their categories
filtered_df = startups_df.loc[filtered_descriptions.index].copy()
filtered_df['Category'] = kmeans_filtered.labels_

# Display the distribution of the new categories
filtered_category_counts = filtered_df['Category'].value_counts()

# Generate a word cloud from the tokens for the presentation
all_descriptions_basic = ' '.join(filtered_df['Please Describe your idea in 1 short paragraph (100-150 words)'].dropna())
tokens_basic = all_descriptions_basic.split()
word_freq_basic = Counter(tokens_basic)
wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_freq_basic)

# Save the word cloud to an image file
wordcloud_image_path = 'wordcloud.png'
wordcloud.to_file(wordcloud_image_path)

# Function to display sample descriptions from each category
def display_sample_descriptions(df, n_samples=3):
    samples_dict = {}
    for category in df['Category'].unique():
        samples = df[df['Category'] == category]['Please Describe your idea in 1 short paragraph (100-150 words)'].head(n_samples).tolist()
        samples_dict[category] = samples
    return samples_dict

samples_dict = display_sample_descriptions(filtered_df)

# PDF Generation
class PDF(FPDF):
    def header(self):
        self.set_font('DejaVu', 'B', 12)
        self.cell(0, 10, 'Startup Data Analysis', 0, 1, 'C')

    def chapter_title(self, title):
        self.set_font('DejaVu', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(10)

    def chapter_body(self, body):
        self.set_font('DejaVu', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_wordcloud(self, image_path):
        self.image(image_path, x=10, y=None, w=190)
        self.ln(105)

# Create PDF
pdf = PDF()

# Add DejaVu font that supports Unicode characters
pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)

pdf.add_page()

# Overview
pdf.chapter_title('Overview')
pdf.chapter_body(
    "This document provides an analysis of startup descriptions. "
    "The dataset was clustered into different categories based on the descriptions provided by the startups. "
    "Key insights and visualizations are presented."
)

# Category Distribution
pdf.chapter_title('Category Distribution')
pdf.chapter_body('\n'.join([f"Category {category}: {count} startups" for category, count in filtered_category_counts.items()]))

# Sample Descriptions
pdf.chapter_title('Sample Descriptions')
for category, samples in samples_dict.items():
    pdf.chapter_body(f"Category {category}:")
    for i, description in enumerate(samples, 1):
        pdf.chapter_body(f"  Sample {i}: {description[:150]}...")

# Word Cloud
pdf.chapter_title('Word Cloud of Descriptions')
pdf.add_wordcloud(wordcloud_image_path)

# Save PDF
pdf_output = 'startup_analysis.pdf'
pdf.output(pdf_output)

pdf_output
