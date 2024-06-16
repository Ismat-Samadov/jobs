import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

# Data for visualizations
years = np.arange(2023, 2033)
market_size = [325.78, 346.68, 368.92, 392.58, 417.72, 444.43, 472.79, 502.89, 534.82, 572.87]

# Revenue Projections
revenue_years = np.arange(1, 5)
revenue_projections = [100000, 300000, 600000, 1000000]

# Revenue Model Breakdown
revenue_sources = ['Premium Subscriptions', 'Advertising', 'Partnerships', 'Referral Program', 'Commission on Placements', 'Data Insights and Analytics']
revenue_amounts = [200000, 150000, 100000, 50000, 75000, 25000]

# Insights Data
market_trends = ['Digital Transformation', 'Remote Work', 'Mobile Recruiting', 'Diversity & Inclusion']
trend_impact = [30, 25, 20, 25]
user_demographics = ['Age 18-24', 'Age 25-34', 'Age 35-44', 'Age 45-54', 'Age 55+']
demographic_percentages = [15, 35, 25, 15, 10]

# Technology Adoption Rates
tech_adoption_years = np.arange(2020, 2030)
tech_adoption_rates = [30, 35, 40, 50, 60, 70, 80, 85, 90, 95]

# User Engagement Metrics
engagement_metrics = ['Monthly Active Users', 'Daily Active Users', 'Average Session Duration (min)', 'Retention Rate (%)']
engagement_values = [50000, 10000, 30, 70]  # Example values

# Create a PDF file
with PdfPages('Job_Vacancy_Platform_Presentation.pdf') as pdf:

    # Slide 1: Market Opportunity
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(years, market_size, marker='o')
    ax.set_title('Market Opportunity', fontsize=20)
    ax.set_xlabel('Year', fontsize=16)
    ax.set_ylabel('Market Size (Billion USD)', fontsize=16)
    ax.grid(True)
    ax.annotate('CAGR: 6.4%', xy=(2023, 325.78), xytext=(2025, 400), fontsize=14, arrowprops=dict(facecolor='black', shrink=0.05))
    plt.figtext(0.1, 0.02, 'Key Trends: Digital Transformation, Remote Work, Mobile Recruiting, Diversity & Inclusion', fontsize=12)
    pdf.savefig(fig)
    plt.close()

    # Slide 2: Revenue Model
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.pie(revenue_amounts, labels=revenue_sources, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired(np.arange(len(revenue_sources))))
    ax.set_title('Revenue Model', fontsize=20)
    plt.figtext(0.1, 0.02, 'Freemium Model: Free Tier and Premium Subscriptions\nAdvertising: Targeted Ads and Sponsored Listings\nPartnerships: Recruitment Agencies and Educational Institutions\nReferral Program: Bonuses for Successful Placements\nCommission on Placements: Success-Based Fees\nData Insights and Analytics: Market Reports and Custom Analytics', fontsize=12)
    pdf.savefig(fig)
    plt.close()

    # Slide 3: Financial Projections
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(revenue_years, revenue_projections, color='skyblue')
    ax.set_title('Financial Projections', fontsize=20)
    ax.set_xlabel('Years', fontsize=16)
    ax.set_ylabel('Revenue (USD)', fontsize=16)
    ax.set_xticks(revenue_years)
    ax.set_xticklabels(['Year 1', 'Year 2', 'Year 3', 'Year 4'], fontsize=14)
    ax.grid(True)
    plt.figtext(0.1, 0.02, 'Initial Investment: $500,000\nRevenue Projections: Year 1 - $100,000, Year 2 - $300,000, Year 3 - $600,000, Year 4 - $1,000,000', fontsize=12)
    pdf.savefig(fig)
    plt.close()

    # Slide 4: Market Insights
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Subplot 1: Market Trends
    ax1 = plt.subplot(121)
    ax1.barh(market_trends, trend_impact, color='lightblue')
    ax1.set_title('Market Trends', fontsize=14)
    ax1.set_xlabel('Impact (%)', fontsize=12)
    
    # Subplot 2: User Demographics
    ax2 = plt.subplot(122)
    ax2.pie(demographic_percentages, labels=user_demographics, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired(np.arange(len(user_demographics))))
    ax2.set_title('User Demographics', fontsize=14)
    
    fig.suptitle('Market Insights', fontsize=20)
    plt.figtext(0.1, 0.02, 'Understanding key trends and user demographics helps in tailoring our platform to meet market demands effectively.', fontsize=12)
    pdf.savefig(fig)
    plt.close()

    # Slide 5: Technology Adoption Rates
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(tech_adoption_years, tech_adoption_rates, marker='o', linestyle='--', color='green')
    ax.set_title('Technology Adoption Rates', fontsize=20)
    ax.set_xlabel('Year', fontsize=16)
    ax.set_ylabel('Adoption Rate (%)', fontsize=16)
    ax.grid(True)
    plt.figtext(0.1, 0.02, 'Projected increase in technology adoption rates from 2020 to 2030.', fontsize=12)
    pdf.savefig(fig)
    plt.close()

    # Slide 6: User Engagement Metrics
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(engagement_metrics, engagement_values, color='purple')
    ax.set_title('User Engagement Metrics', fontsize=20)
    ax.set_xlabel('Metrics', fontsize=16)
    ax.set_ylabel('Values', fontsize=16)
    plt.figtext(0.1, 0.02, 'Metrics indicating user engagement on the platform.', fontsize=12)
    pdf.savefig(fig)
    plt.close()
