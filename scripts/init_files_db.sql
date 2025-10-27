-- File Management System Schema
-- Create tables for managing uploaded files and folders

-- Create folders table
CREATE TABLE IF NOT EXISTS leads.folders (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INTEGER REFERENCES leads.folders(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES leads.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, parent_id)
);

-- Create files table
CREATE TABLE IF NOT EXISTS leads.files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- 'csv', 'xlsx', 'json', etc.
    file_size BIGINT NOT NULL,
    file_path TEXT NOT NULL,
    folder_id INTEGER REFERENCES leads.folders(id) ON DELETE CASCADE,
    uploaded_by INTEGER REFERENCES leads.users(id),
    description TEXT,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON leads.folders(parent_id);
CREATE INDEX IF NOT EXISTS idx_folders_name ON leads.folders(name);
CREATE INDEX IF NOT EXISTS idx_files_folder_id ON leads.files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_filename ON leads.files(filename);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON leads.files(file_type);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION leads.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to auto-update updated_at
CREATE TRIGGER update_folders_updated_at BEFORE UPDATE ON leads.folders
    FOR EACH ROW EXECUTE FUNCTION leads.update_updated_at_column();

CREATE TRIGGER update_files_updated_at BEFORE UPDATE ON leads.files
    FOR EACH ROW EXECUTE FUNCTION leads.update_updated_at_column();

-- Insert root folder (optional, for organization)
INSERT INTO leads.folders (id, name, parent_id)
VALUES (1, 'Root', NULL)
ON CONFLICT DO NOTHING;
