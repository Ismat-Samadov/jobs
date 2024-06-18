import pandas as pd
from googletrans import Translator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import utils

# Load your CSV file
file_path = 'scraped_data.csv'  # Update with your file path
data = pd.read_csv(file_path, encoding='utf-8')

# Clean the data by removing rows with placeholder values ('.')
cleaned_data = data[(data != '.').all(axis=1)]

# Initialize the translator
translator = Translator()

# Define a function to translate text
def translate_text(text, dest='en'):
    try:
        return translator.translate(text, dest=dest).text
    except Exception as e:
        return str(e)

# Translate the relevant columns
cleaned_data['translated_description'] = cleaned_data['Please Describe your idea in 1 short paragraph (100-150 words)'].apply(lambda x: translate_text(x))
cleaned_data['translated_problems'] = cleaned_data['What Problem(s) does your project solve? (give in bullet points)'].apply(lambda x: translate_text(x))

# Combine translated text for clustering
cleaned_data['combined_text'] = cleaned_data.apply(lambda row: ' '.join([row['translated_description'], row['translated_problems']]), axis=1)

# Vectorize the combined text using TF-IDF
vectorizer = TfidfVectorizer(stop_words='english')
X = vectorizer.fit_transform(cleaned_data['combined_text'])

# Define your idea's text (translated version)
your_translated_idea_text = """
A Unified Job Vacancy Platform Connecting Job Seekers and Employers in Real-Time.
This project is a comprehensive job vacancy platform that integrates a powerful backend API, two distinct frontend deployments, and a Telegram bot. 
The backend scrapes job data from various websites, stores it in a PostgreSQL database, and serves it via an API to both frontends and the Telegram bot. 
The Streamlit frontend offers an interactive, Python-driven interface for exploring job vacancies, while the traditional web frontend provides a responsive HTML/CSS/JavaScript interface. 
The Telegram bot enables users to query job vacancies in real-time, providing a seamless and user-friendly job search experience across multiple platforms.
"""

# Vectorize your idea's text
your_idea_vector = vectorizer.transform([your_translated_idea_text])

# Compute cosine similarity between your idea and the dataset
similarities = cosine_similarity(your_idea_vector, X).flatten()

# Find the indices of the most similar ideas
similar_idea_indices = similarities.argsort()[-5:][::-1]  # Get top 5 similar ideas

# Extract the most similar ideas from the dataset
similar_ideas = cleaned_data.iloc[similar_idea_indices]

# Define more detailed advantages and disadvantages based on general assessments
def analyze_advantages_disadvantages(description):
    if "job" in description.lower():
        return (
            "Advantages: \n- Centralized platform simplifies job search for seekers and posting for employers.\n"
            "- Real-time updates enhance user experience.\n"
            "- Multiple interfaces cater to different user preferences.",
            "Disadvantages: \n- High initial development and maintenance cost.\n"
            "- Dependence on external data sources for scraping job listings.\n"
            "- Requires continuous updating to remain competitive."
        )
    elif "recruitment" in description.lower():
        return (
            "Advantages: \n- Automation reduces manual effort and time.\n"
            "- AI-driven insights enhance accuracy and consistency.\n"
            "- Detailed analytics improve decision-making.",
            "Disadvantages: \n- High complexity and cost of AI implementation.\n"
            "- Potential for bias in AI-generated recommendations.\n"
            "- Requires robust data privacy and security measures."
        )
    elif "discount" in description.lower() or "offer" in description.lower():
        return (
            "Advantages: \n- Centralizes discounts and offers from multiple sources.\n"
            "- Personalization enhances user experience.\n"
            "- Notifications ensure users never miss a deal.",
            "Disadvantages: \n- Requires partnerships with multiple platforms for data.\n"
            "- Needs continuous updates to track new discounts.\n"
            "- Potential overload of notifications for users."
        )
    elif "relocation" in description.lower():
        return (
            "Advantages: \n- Comprehensive support for newcomers reduces stress.\n"
            "- Centralized platform streamlines access to multiple services.\n"
            "- Customized guidance enhances user experience.",
            "Disadvantages: \n- High complexity in integrating various services.\n"
            "- Requires partnerships with local service providers.\n"
            "- Needs continuous updates and support for users."
        )
    elif "internal" in description.lower() or "employee" in description.lower():
        return (
            "Advantages: \n- Streamlined internal job application process.\n"
            "- Enhances employee retention within the group.\n"
            "- Centralized platform saves time for employees and HR.",
            "Disadvantages: \n- Limited to employees within the organization.\n"
            "- High dependency on the platform's user-friendliness.\n"
            "- Requires continuous updates to keep up with internal job openings."
        )
    else:
        return "Advantages: TBD", "Disadvantages: TBD"

similar_ideas['advantages'] = similar_ideas['translated_description'].apply(lambda x: analyze_advantages_disadvantages(x)[0])
similar_ideas['disadvantages'] = similar_ideas['translated_description'].apply(lambda x: analyze_advantages_disadvantages(x)[1])

# Create a new PDF document
pdf_path_detailed = "Similar_Ideas_Analysis_Detailed.pdf"
c = canvas.Canvas(pdf_path_detailed, pagesize=letter)
width, height = letter

# Title
c.setFont("Helvetica-Bold", 16)
c.drawString(100, height - 50, "Analysis of Similar Ideas")

# Function to add wrapped text to the PDF
def draw_wrapped_text(c, text, x, y, max_width):
    lines = utils.simpleSplit(text, "Helvetica", 10, max_width)
    for line in lines:
        if y < 40:  # Check for page overflow
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50
        c.drawString(x, y, line)
        y -= 12
    return y - 12

# Add each similar idea to the PDF
y_position = height - 100
max_width = 500  # Define the maximum width for text wrapping

for idx in range(len(similar_ideas)):
    if y_position < 100:  # If we reach the bottom of the page, add a new page
        c.showPage()
        y_position = height - 50
    
    row = similar_ideas.iloc[idx]
    similarity = similarities[similar_idea_indices[idx]]
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y_position, f"Idea {idx+1}")
    y_position -= 20
    
    c.setFont("Helvetica", 10)
    y_position = draw_wrapped_text(c, "Description:", 30, y_position, max_width)
    y_position = draw_wrapped_text(c, row['translated_description'], 30, y_position, max_width)
    
    y_position = draw_wrapped_text(c, "Problems Solved:", 30, y_position, max_width)
    y_position = draw_wrapped_text(c, row['translated_problems'], 30, y_position, max_width)
    
    y_position = draw_wrapped_text(c, "Advantages:", 30, y_position, max_width)
    y_position = draw_wrapped_text(c, row['advantages'], 30, y_position, max_width)
    
    y_position = draw_wrapped_text(c, "Disadvantages:", 30, y_position, max_width)
    y_position = draw_wrapped_text(c, row['disadvantages'], 30, y_position, max_width)
    
    y_position = draw_wrapped_text(c, "Similarity Score:", 30, y_position, max_width)
    y_position = draw_wrapped_text(c, str(similarity), 150, y_position, max_width)
    
    y_position -= 10  # Add a blank line for spacing

# Save the PDF
c.save()

print(f"PDF report saved as {pdf_path_detailed}")
