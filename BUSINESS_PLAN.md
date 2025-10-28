# Business Plan & Model - Lead Generator Platform

## Executive Summary

**Company Name:** Bir.guru Lead Generator

**Mission:** To revolutionize B2B lead generation in Azerbaijan by providing businesses with verified, high-quality contact information and intelligent lead management tools.

**Vision:** Become the leading lead generation and CRM platform in the Caucasus region, empowering businesses to grow through data-driven sales strategies.

**Product:** An AI-powered lead generation platform that automatically discovers, validates, and manages business contacts from multiple online sources, with integrated CRM capabilities and file management.

---

## 1. Problem Statement

### Current Market Challenges:
- **Manual Lead Collection:** Sales teams waste 40-50% of their time manually searching for leads on websites like turbo.az, tap.az, villa.az, and bul.az
- **Invalid Contact Data:** 30-40% of manually collected phone numbers are invalid, disconnected, or incorrectly formatted
- **Data Duplication:** Companies repeatedly collect the same leads, wasting time and resources
- **Poor Organization:** Leads stored in Excel sheets, notebooks, or scattered across multiple systems
- **No Follow-up System:** Businesses lose potential customers due to lack of structured follow-up processes

### Target Market Pain Points:
1. Real estate agencies spending hours collecting property owner contacts
2. Auto dealerships manually tracking car seller information
3. B2B service providers struggling to find potential clients
4. Marketing agencies needing verified contact databases
5. Startups requiring cost-effective lead generation solutions

---

## 2. Solution

### Core Features:

#### 2.1 Automated Lead Scraping
- **Multi-source Integration:** Automatic data collection from turbo.az, tap.az, villa.az, bul.az, and other platforms
- **Smart Parsing:** AI-powered extraction of business names, phone numbers, websites, and metadata
- **Real-time Validation:** Phone number verification using Azerbaijan's numbering standards
- **Deduplication:** Automatic removal of duplicate entries across all sources

#### 2.2 Lead Management System
- **Centralized Database:** PostgreSQL-based secure storage with full-text search
- **Lead Status Tracking:** Monitor leads through entire sales pipeline (new → contacted → qualified → converted)
- **Contact History:** Complete timeline of all interactions with each lead
- **Bulk Operations:** Efficiently manage thousands of leads with batch operations

#### 2.3 File Management & Organization
- **Cloudflare R2 Storage:** Secure, scalable file storage for contracts, presentations, and documents
- **Folder Organization:** Hierarchical folder structure for project-based file management
- **Direct Upload:** High-performance direct-to-cloud uploads without server bottlenecks
- **Access Control:** Role-based permissions (Admin/User) for secure collaboration

#### 2.4 Admin Dashboard
- **Real-time Analytics:** Track lead conversion rates, source performance, and team activity
- **User Management:** Multi-user support with role-based access control
- **Source Configuration:** Manage and monitor scraping sources
- **Export Capabilities:** Download leads in CSV/Excel format for external use

---

## 3. Business Model

### 3.1 Revenue Streams

#### Primary: SaaS Subscription Model

| Tier | Price (Monthly) | Leads/Month | Users | Features |
|------|----------------|-------------|-------|----------|
| **Starter** | $49 | 1,000 leads | 1 user | Basic scraping, lead management |
| **Professional** | $149 | 5,000 leads | 3 users | All sources, analytics, file storage (10GB) |
| **Business** | $349 | 15,000 leads | 10 users | Priority support, API access, file storage (50GB) |
| **Enterprise** | Custom | Unlimited | Unlimited | Custom integrations, dedicated support, unlimited storage |

#### Secondary Revenue Streams:
1. **Pay-per-Lead:** $0.10 per lead for users exceeding monthly quota
2. **Data Enrichment Services:** Additional contact information (emails, social profiles) at $0.05 per enriched lead
3. **API Access:** $299/month for external CRM integration
4. **White-label Solutions:** Custom pricing for agencies wanting branded versions
5. **Premium Support:** $99/month for priority technical support and consultation

### 3.2 Cost Structure

#### Fixed Costs (Monthly):
- **Infrastructure:**
  - Cloudflare R2 Storage: $15/TB
  - PostgreSQL Database (Supabase): $25
  - Next.js Hosting (Vercel): $20
  - Domain & SSL: $5
  - **Total Infrastructure: ~$65/month**

- **Operations:**
  - Development & Maintenance: $2,000
  - Customer Support (part-time): $500
  - Marketing & Sales: $1,000
  - Legal & Accounting: $200
  - **Total Operations: ~$3,700/month**

#### Variable Costs:
- Additional storage: $0.015 per GB
- SMS verification (if implemented): $0.02 per verification
- Data enrichment API calls: $0.02 per enriched lead

#### Total Monthly Operating Cost: ~$4,000 (with 100 customers)

### 3.3 Pricing Strategy
- **Free Trial:** 14-day trial with 100 free leads to demonstrate value
- **Annual Discount:** 20% discount for annual subscriptions (improve cash flow)
- **Volume Discounts:** Custom pricing for enterprises (>20 users)
- **Referral Program:** 20% commission for 3 months on referred customers

---

## 4. Market Analysis

### 4.1 Target Market

#### Primary Markets:
1. **Real Estate Agencies (Azerbaijan):** 500+ agencies
2. **Auto Dealerships:** 300+ dealerships
3. **B2B Service Companies:** 2,000+ companies
4. **Marketing Agencies:** 150+ agencies
5. **Startups & SMBs:** 5,000+ potential users

#### Market Size:
- **TAM (Total Addressable Market):** $12M/year (all B2B companies in Azerbaijan needing lead generation)
- **SAM (Serviceable Addressable Market):** $3M/year (companies actively using online lead sources)
- **SOM (Serviceable Obtainable Market):** $300K/year (realistic 3-year target: 10% of SAM)

### 4.2 Competitive Analysis

| Competitor | Strengths | Weaknesses | Our Advantage |
|------------|-----------|------------|---------------|
| **Manual Collection** | Free, familiar | Time-consuming, error-prone | 95% time savings, validation |
| **Excel/Spreadsheets** | Free, simple | No automation, no validation | Automated scraping, deduplication |
| **International CRMs** (Salesforce, HubSpot) | Feature-rich | Expensive ($100+/user), not localized | 70% cheaper, Azerbaijan-focused |
| **Local Competitors** | Local knowledge | Limited features, poor UX | Superior tech, modern interface |

### 4.3 Competitive Advantages
1. **Local Market Expertise:** Deep integration with Azerbaijan's top lead sources
2. **Phone Validation:** Proprietary Azerbaijan phone number validation
3. **Cost-Effective:** 50-70% cheaper than international alternatives
4. **All-in-One Platform:** Scraping + CRM + File Management in one tool
5. **Modern Technology:** Built on latest Next.js, React, PostgreSQL stack

---

## 5. Go-to-Market Strategy

### 5.1 Customer Acquisition

#### Phase 1: Early Adopters (Months 1-3)
- **Target:** 20 pilot customers
- **Strategy:**
  - Direct outreach to real estate agencies and auto dealerships
  - Offer 50% discount for first 3 months
  - Gather testimonials and case studies
- **Channels:**
  - LinkedIn direct messages
  - Industry events and meetups
  - Personal network referrals

#### Phase 2: Growth (Months 4-12)
- **Target:** 100 paying customers
- **Strategy:**
  - Content marketing (blog posts on lead generation)
  - SEO for keywords like "azerbaijan lead generation", "turbo.az scraper"
  - Facebook/Instagram ads targeting business owners
  - Partnership with industry associations
- **Channels:**
  - Paid advertising (Google Ads, Facebook Ads)
  - Content marketing & SEO
  - Webinars and demos
  - Referral program

#### Phase 3: Scale (Months 13-36)
- **Target:** 500+ customers
- **Strategy:**
  - Sales team (2-3 salespeople)
  - Channel partnerships with IT agencies
  - Regional expansion (Georgia, Turkey)
  - Enterprise sales focus
- **Channels:**
  - Outbound sales team
  - Partner network
  - Industry conferences
  - PR and media coverage

### 5.2 Marketing Budget (Year 1)

| Channel | Monthly Budget | Annual Budget |
|---------|---------------|---------------|
| Paid Advertising | $1,500 | $18,000 |
| Content Marketing | $500 | $6,000 |
| Events & Conferences | $300 | $3,600 |
| Referral Program | $200 | $2,400 |
| **Total** | **$2,500** | **$30,000** |

### 5.3 Sales Process
1. **Awareness:** Content marketing, ads, referrals
2. **Interest:** Free trial signup
3. **Consideration:** Automated email sequence with tips and best practices
4. **Decision:** Demo call with sales team (for Pro+ plans)
5. **Purchase:** Self-service checkout or sales-assisted
6. **Retention:** Onboarding sequence, regular check-ins, success stories

---

## 6. Financial Projections

### 6.1 Revenue Forecast (3 Years)

#### Year 1:
| Quarter | Customers | MRR | ARR | Churn Rate |
|---------|-----------|-----|-----|------------|
| Q1 | 10 | $990 | $11,880 | 10% |
| Q2 | 30 | $3,470 | $41,640 | 8% |
| Q3 | 60 | $7,940 | $95,280 | 7% |
| Q4 | 100 | $14,900 | $178,800 | 5% |

**Year 1 Total Revenue:** $178,800

#### Year 2:
- Target: 300 customers
- Average Revenue Per Account (ARPA): $165/month
- **Year 2 Revenue:** $594,000
- Churn Rate: 4% monthly

#### Year 3:
- Target: 500 customers
- ARPA: $180/month (increased through upsells)
- **Year 3 Revenue:** $1,080,000
- Churn Rate: 3% monthly

### 6.2 Cost Projections

#### Year 1 Costs:
- Infrastructure: $780
- Development: $24,000
- Operations: $18,000
- Marketing: $30,000
- Legal & Admin: $5,000
- **Total Year 1 Costs:** $77,780

#### Year 1 Net Profit: $101,020

#### Year 2 Costs:
- Infrastructure: $3,000
- Team (3 people): $90,000
- Marketing: $60,000
- Operations: $30,000
- **Total Year 2 Costs:** $183,000

#### Year 2 Net Profit: $411,000

### 6.3 Break-Even Analysis
- **Fixed Monthly Costs:** $4,000
- **Average Revenue Per Customer:** $149
- **Break-Even Point:** 27 customers
- **Expected Time to Break-Even:** Month 2

---

## 7. Team & Organization

### Current Team:
- **Founder/CEO:** Full-stack development, product strategy
- **Technical Infrastructure:** Next.js, PostgreSQL, Python scraping

### Year 1 Hiring Plan:
- **Q2:** Part-time Customer Support Specialist
- **Q3:** Junior Developer / DevOps Engineer
- **Q4:** Sales/Marketing Manager

### Year 2 Hiring Plan:
- Sales Representatives (2)
- Full-time Customer Success Manager
- Senior Backend Developer
- UI/UX Designer

---

## 8. Technology Stack

### Frontend:
- **Framework:** Next.js 14 (React)
- **Styling:** Tailwind CSS
- **Authentication:** NextAuth.js
- **State Management:** React Hooks

### Backend:
- **Database:** PostgreSQL (Supabase)
- **API:** Next.js API Routes
- **File Storage:** Cloudflare R2
- **Authentication:** JWT tokens

### Scraping & Automation:
- **Language:** Python 3
- **Libraries:** BeautifulSoup, Requests, Playwright
- **Validation:** Custom phone number validator
- **Scheduling:** Cron jobs

### Infrastructure:
- **Hosting:** Vercel (frontend), Railway/Render (Python workers)
- **Storage:** Cloudflare R2
- **CDN:** Cloudflare
- **Monitoring:** Vercel Analytics

---

## 9. Key Metrics (KPIs)

### Product Metrics:
- **Leads Scraped per Day:** Target 10,000+
- **Phone Validation Accuracy:** >95%
- **Scraping Success Rate:** >90%
- **System Uptime:** 99.5%

### Business Metrics:
- **Monthly Recurring Revenue (MRR)**
- **Customer Acquisition Cost (CAC):** Target <$200
- **Lifetime Value (LTV):** Target >$1,500
- **LTV:CAC Ratio:** Target 7.5:1
- **Churn Rate:** Target <5% monthly
- **Net Revenue Retention:** Target >100%

### User Engagement:
- **Daily Active Users (DAU)**
- **Weekly Active Users (WAU)**
- **Average Leads per Customer per Month**
- **Feature Adoption Rate**
- **Customer Satisfaction Score (CSAT):** Target >4.5/5

---

## 10. Risk Analysis & Mitigation

### Technical Risks:
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Website structure changes break scrapers | High | Medium | Modular scraper design, automated testing, quick updates |
| Database performance issues | Medium | Low | Query optimization, caching, scalable infrastructure |
| Security breach | High | Low | Regular security audits, encryption, GDPR compliance |

### Business Risks:
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Legal issues with web scraping | High | Medium | robots.txt compliance, terms of service review, legal consultation |
| High customer churn | High | Medium | Strong onboarding, customer success program, continuous value delivery |
| Competitor with more funding | Medium | Medium | Focus on local expertise, customer relationships, faster iteration |
| Economic downturn | Medium | Low | Diverse customer base, essential tool positioning, flexible pricing |

### Regulatory Risks:
- **Data Protection:** Comply with Azerbaijan data protection laws
- **Web Scraping Legality:** Follow robots.txt, avoid aggressive scraping
- **Phone Number Privacy:** Only collect publicly available business numbers
- **Mitigation:** Legal consultation, clear terms of service, privacy policy

---

## 11. Milestones & Timeline

### Q1 2025 (Current):
- ✅ MVP Development Complete
- ✅ Multi-source scraping (turbo.az, tap.az, villa.az, bul.az)
- ✅ Lead management system
- ✅ File manager with R2 integration
- ✅ Admin dashboard
- 🎯 Launch beta with 5-10 pilot customers

### Q2 2025:
- 🎯 20 paying customers
- 🎯 Implement email scraping functionality
- 🎯 Add lead scoring algorithm
- 🎯 Launch referral program
- 🎯 Build case studies and testimonials

### Q3 2025:
- 🎯 50 paying customers
- 🎯 API access for integrations
- 🎯 Mobile app (iOS/Android)
- 🎯 Advanced analytics dashboard
- 🎯 Hire first employee

### Q4 2025:
- 🎯 100 paying customers
- 🎯 Break $15K MRR
- 🎯 Launch enterprise tier
- 🎯 Expand to Georgia market
- 🎯 Raise seed funding (optional)

### 2026:
- 🎯 300 paying customers
- 🎯 $50K MRR
- 🎯 Build sales team
- 🎯 Major feature releases (email campaigns, calling integration)
- 🎯 Series A fundraising (if scaling internationally)

---

## 12. Funding Requirements

### Bootstrap Path (Recommended):
- **Initial Investment:** $10,000
  - Infrastructure setup: $2,000
  - Legal & incorporation: $1,500
  - Initial marketing: $3,000
  - Operating buffer: $3,500
- **Funding Source:** Founder capital, revenue reinvestment
- **Timeline:** Self-sustainable by Month 3

### Seed Funding Path (Optional):
- **Raise Amount:** $150,000
- **Use of Funds:**
  - Product Development: $50,000 (2 developers for 6 months)
  - Sales & Marketing: $60,000
  - Operations: $25,000
  - Legal & Admin: $15,000
- **Equity Offered:** 10-15%
- **Target Investors:** Local angel investors, Azerbaijan tech funds, regional VCs

### Series A (Future - Year 2):
- **Raise Amount:** $1-2M
- **Purpose:** Regional expansion, sales team, enterprise features
- **Timeline:** 18-24 months after launch

---

## 13. Exit Strategy

### Potential Exit Scenarios:

1. **Acquisition by Regional Tech Company (3-5 years)**
   - Potential acquirers: Local CRM companies, regional tech players
   - Target valuation: $3-5M

2. **Acquisition by International CRM/Sales Tech Platform (5-7 years)**
   - Potential acquirers: Salesforce, HubSpot, Pipedrive, Close
   - Target valuation: $10-20M

3. **Merger with Complementary Service (3-5 years)**
   - Merge with marketing automation or analytics platform
   - Create comprehensive sales & marketing suite

4. **Continue as Profitable Business (Lifestyle Business)**
   - No exit, continue growing and taking distributions
   - Long-term sustainable revenue stream

---

## 14. Success Factors

### Critical Success Factors:
1. **Data Quality:** Maintaining >95% phone validation accuracy
2. **Customer Success:** Ensuring customers see ROI within first month
3. **Product Velocity:** Shipping new features monthly
4. **Local Market Knowledge:** Deep understanding of Azerbaijan business landscape
5. **Scalable Infrastructure:** Handling growth without performance degradation

### Unique Value Proposition:
"The only lead generation platform built specifically for Azerbaijan businesses - automatically find, validate, and manage thousands of local B2B contacts in minutes, not days."

---

## 15. Conclusion

Bir.guru Lead Generator addresses a critical pain point in the Azerbaijan B2B market: inefficient, manual lead generation. With a proven MVP, clear monetization strategy, and significant market opportunity, we are positioned to become the leading sales intelligence platform in the region.

### Investment Highlights:
- ✅ Working product with real users
- ✅ Clear path to profitability (Month 3)
- ✅ Large addressable market ($3M SAM)
- ✅ Strong unit economics (LTV:CAC = 7.5:1)
- ✅ Scalable SaaS model
- ✅ Defensible technology with local expertise
- ✅ Multiple exit opportunities

### Call to Action:
We are seeking pilot customers and strategic partners to validate our product-market fit. Join us in revolutionizing how Azerbaijan businesses generate and manage leads.

**Contact:** [Your Contact Information]
**Website:** https://www.bir.guru
**Demo:** Schedule a live demo to see the platform in action

---

*Document Version: 1.0*
*Last Updated: January 2025*
*Confidential - For Internal and Investor Use Only*
