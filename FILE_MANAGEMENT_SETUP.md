# File Management System - Setup Guide

## Overview

A comprehensive file management system has been added to your Lead Generator application, allowing admins to upload, organize, and manage CSV, XLSX, JSON, and other data files, while regular users can browse and download these files.

## Features

### For Admin Users:
- ✅ **Upload Files** - Support for CSV, XLSX, XLS, JSON, TXT files
- ✅ **Create Folders** - Organize files in a hierarchical folder structure
- ✅ **Edit Files** - Rename files and update descriptions
- ✅ **Move Files** - Reorganize files between folders
- ✅ **Delete Files & Folders** - Remove unwanted items
- ✅ **Full CRUD Operations** - Complete control over file management

### For Regular Users:
- ✅ **Browse Files** - View all uploaded files and folders
- ✅ **Download Files** - Download any file with one click
- ✅ **Download Counter** - Track how many times files have been downloaded
- ✅ **Folder Navigation** - Navigate through folder hierarchy

## Database Setup

### Step 1: Run the Database Migration

Execute the SQL schema to create the necessary tables:

```bash
# If you have DATABASE_URL environment variable set:
psql $DATABASE_URL -f scripts/init_files_db.sql

# Or manually connect to your database and run:
psql -h your-host -U your-user -d your-database -f scripts/init_files_db.sql
```

This will create:
- **leads.folders** table - Stores folder structure
- **leads.files** table - Stores file metadata
- Indexes for performance optimization
- Triggers for automatic timestamp updates

### Step 2: Verify Tables Were Created

```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'leads'
AND table_name IN ('folders', 'files');

-- Check folder structure
SELECT * FROM leads.folders;

-- Check files
SELECT * FROM leads.files;
```

## File Storage Setup

### Create Uploads Directory

The application stores uploaded files in the `uploads/` directory:

```bash
mkdir -p uploads
```

**Important:** Make sure this directory has proper write permissions:

```bash
chmod 755 uploads
```

### For Production (Vercel/Cloud Deployment):

Note: Vercel's serverless functions have ephemeral file systems. For production, consider:

1. **Option A: Use Cloud Storage**
   - AWS S3
   - Google Cloud Storage
   - Azure Blob Storage
   - Cloudflare R2

2. **Option B: Use Vercel Blob Storage** (Recommended)
   ```bash
   npm install @vercel/blob
   ```

## Navigation Structure

### Admin Flow:
```
Dashboard → [Files] → Browse & Download
         ↓
    [Manage Files] → Upload, Create Folders, Edit, Move, Delete
```

### User Flow:
```
Dashboard → [Files] → Browse & Download Only
```

## API Routes

### Files API (`/api/files`)
- `GET` - List all files (with optional folder filter)
- `POST` - Upload a new file (Admin only)
- `PUT` - Update file metadata (Admin only)
- `DELETE` - Delete a file (Admin only)

### Download API (`/api/files/download`)
- `GET?id={fileId}` - Download a specific file

### Folders API (`/api/folders`)
- `GET` - List all folders with hierarchy
- `POST` - Create a new folder (Admin only)
- `PUT` - Rename or move a folder (Admin only)
- `DELETE` - Delete an empty folder (Admin only)

## Pages

### `/files` - Files Browser (All Users)
- View all files and folders
- Navigate folder structure
- Download files
- View file metadata (size, download count, upload date)

### `/file-manager` - File Manager (Admin Only)
- Full CRUD operations
- Upload new files
- Create folders
- Edit file names and descriptions
- Move files between folders
- Delete files and folders
- Folder management with breadcrumb navigation

## Supported File Types

The system accepts the following file formats:
- **CSV** (`.csv`) - Comma-separated values
- **Excel** (`.xlsx`, `.xls`) - Spreadsheet files
- **JSON** (`.json`) - Structured data
- **Text** (`.txt`) - Plain text files

To add more file types, update the `allowedTypes` array in `/app/api/files/route.ts`:

```typescript
const allowedTypes = ['.csv', '.xlsx', '.xls', '.json', '.txt', '.pdf'];
```

## Security Features

### Authentication & Authorization:
- ✅ All file operations require authentication
- ✅ Upload, edit, move, delete operations restricted to admin role
- ✅ Middleware protection on `/file-manager` route
- ✅ API-level role checking on all admin endpoints

### File Validation:
- ✅ File type validation (whitelist approach)
- ✅ Filename sanitization (removes special characters)
- ✅ Unique filenames with timestamp prefixes

### Database Protection:
- ✅ Parameterized SQL queries (prevents SQL injection)
- ✅ Foreign key constraints
- ✅ Cascade delete protection

## Database Schema

### Folders Table
```sql
CREATE TABLE leads.folders (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INTEGER REFERENCES leads.folders(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, parent_id)
);
```

### Files Table
```sql
CREATE TABLE leads.files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    file_path TEXT NOT NULL,
    folder_id INTEGER REFERENCES leads.folders(id) ON DELETE CASCADE,
    uploaded_by INTEGER REFERENCES users(id),
    description TEXT,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage Examples

### Admin: Upload a File
1. Navigate to **File Manager** from the navigation bar
2. Click **"Upload File"** button
3. Select a CSV, XLSX, JSON, or TXT file
4. (Optional) Add a description
5. Click **"Upload"**

### Admin: Create a Folder
1. Navigate to **File Manager**
2. Click **"New Folder"** button
3. Enter folder name
4. Click **"Create"**

### Admin: Move a File
1. Navigate to **File Manager**
2. Find the file you want to move
3. Click **"Move"** button
4. Select target folder from dropdown
5. Click **"Move"**

### User: Download a File
1. Navigate to **Files** from the navigation bar
2. Browse folders or scroll through files
3. Click **"Download"** button next to any file
4. File will be downloaded to your device

## Troubleshooting

### Issue: "File upload failed"
**Solution:**
- Check that the `uploads/` directory exists
- Verify directory permissions (should be 755)
- Check file size limits in your server configuration

### Issue: "Folder not found"
**Solution:**
- Run the database migration script again
- Check that the `leads.folders` table exists

### Issue: "Access denied to file manager"
**Solution:**
- Verify your user has admin role in the database
- Check the `users` table: `SELECT role FROM users WHERE username = 'your_username';`

### Issue: "Cannot delete folder"
**Solution:**
- Folders can only be deleted if they're empty
- First delete all files inside the folder
- Then delete any subfolders
- Finally delete the folder itself

## Testing Checklist

- [ ] Database tables created successfully
- [ ] Uploads directory exists with proper permissions
- [ ] Admin can access `/file-manager` page
- [ ] Regular users redirected from `/file-manager` to `/files`
- [ ] Admin can upload a CSV file
- [ ] Admin can create a folder
- [ ] Admin can move files between folders
- [ ] Admin can rename files
- [ ] Admin can delete files
- [ ] Users can browse files
- [ ] Users can download files
- [ ] Download counter increments
- [ ] Folder navigation works (breadcrumbs)

## Maintenance

### Clean Up Old Files
```sql
-- Find files older than 6 months
SELECT id, original_filename, created_at
FROM leads.files
WHERE created_at < NOW() - INTERVAL '6 months';

-- Delete old files (be careful!)
DELETE FROM leads.files
WHERE created_at < NOW() - INTERVAL '6 months';
```

### Check Storage Usage
```sql
-- Get total storage used
SELECT
    COUNT(*) as total_files,
    pg_size_pretty(SUM(file_size)::bigint) as total_size
FROM leads.files;

-- Get storage by file type
SELECT
    file_type,
    COUNT(*) as count,
    pg_size_pretty(SUM(file_size)::bigint) as total_size
FROM leads.files
GROUP BY file_type
ORDER BY SUM(file_size) DESC;
```

## Next Steps

1. **Initialize the database** - Run the SQL migration script
2. **Create uploads directory** - Ensure it has proper permissions
3. **Test as admin** - Try uploading, creating folders, moving files
4. **Test as user** - Try browsing and downloading files
5. **Add your existing files** - Upload your CSV/XLSX files through the admin interface

## Support

If you encounter any issues:
1. Check the browser console for JavaScript errors
2. Check the server logs for API errors
3. Verify database connections and permissions
4. Ensure middleware is protecting routes correctly

---

**Built with:**
- Next.js 14 (App Router)
- TypeScript
- PostgreSQL
- Tailwind CSS
- NextAuth.js for authentication
