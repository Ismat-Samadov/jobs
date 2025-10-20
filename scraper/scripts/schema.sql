-- Create leads schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS leads;

-- Create the universal leads table for all sources
CREATE TABLE IF NOT EXISTS leads.leads (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    website VARCHAR(255) NOT NULL,
    source VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create an index on phone_number for faster lookups
CREATE INDEX IF NOT EXISTS idx_leads_phone_number ON leads.leads(phone_number);

-- Create an index on source for faster lookups
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads.leads(source);

-- Create an index on website for faster lookups
CREATE INDEX IF NOT EXISTS idx_leads_website ON leads.leads(website);
