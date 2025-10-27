# Cloudflare R2 Storage Integration

## Overview

Your file management system now uses **Cloudflare R2** for cloud storage instead of the local filesystem. This makes the application fully compatible with Vercel's serverless deployment and provides scalable, persistent file storage.

## Why R2?

✅ **Zero Egress Fees** - No charges for file downloads (perfect for file sharing!)
✅ **S3-Compatible** - Uses standard AWS SDK
✅ **Persistent Storage** - Files survive serverless restarts
✅ **Scalable** - Handles unlimited file sizes and volumes
✅ **Cost-Effective** - $0.015/GB storage, $0 for bandwidth
✅ **Vercel Compatible** - Works perfectly with serverless deployments

## Configuration

### Environment Variables

Add these to your Vercel project settings:

```env
R2_ACCOUNT_ID=612eb8c2fbc8d81e98c37a03e49f4a8f
R2_ACCESS_KEY_ID=d135ef5010f343efd084a640d3677894
R2_SECRET_ACCESS_KEY=b69c97ad591c33bfa8869e14729d7e742b07255e115fa4d67efd41a5c1366820
R2_BUCKET_NAME=leadgenerator
```

### R2 Bucket Details

- **Bucket Name:** `leadgenerator`
- **Location:** Western Europe (WEUR)
- **S3 Endpoint:** `https://612eb8c2fbc8d81e98c37a03e49f4a8f.r2.cloudflarestorage.com`
- **Public Access:** Disabled (files are private by default)

## How It Works

### File Upload Flow

1. User uploads file through `/file-manager`
2. File is converted to Buffer
3. Unique R2 key is generated: `uploads/{timestamp}_{random}_{filename}`
4. File is uploaded to R2 bucket via AWS SDK
5. Metadata is saved to PostgreSQL database (R2 key stored as `file_path`)

### File Download Flow

1. User clicks download button
2. API fetches file metadata from database
3. File is retrieved from R2 using stored key
4. File is streamed to user's browser
5. Download counter is incremented in database

### File Delete Flow

1. Admin clicks delete button
2. File is deleted from R2 bucket
3. Database record is removed
4. Both operations complete successfully

## API Changes

### Upload API (`/api/files`)

**Before:**
```typescript
await writeFile(localPath, buffer);  // Saved to disk
```

**After:**
```typescript
await uploadToR2(r2Key, buffer, contentType);  // Saved to R2
```

### Download API (`/api/files/download`)

**Before:**
```typescript
const buffer = await readFile(localPath);  // Read from disk
```

**After:**
```typescript
const result = await downloadFromR2(r2Key);  // Fetch from R2
```

### Delete API (`/api/files`)

**Before:**
```typescript
await unlink(localPath);  // Delete from disk
```

**After:**
```typescript
await deleteFromR2(r2Key);  // Delete from R2
```

## R2 Client Library

Located at `/lib/r2.ts`, provides these functions:

### `uploadToR2(key, buffer, contentType)`
Uploads a file to R2 bucket.

```typescript
const result = await uploadToR2(
  'uploads/123_abc_file.csv',
  fileBuffer,
  'text/csv'
);
```

### `downloadFromR2(key)`
Downloads a file from R2 bucket.

```typescript
const result = await downloadFromR2('uploads/123_abc_file.csv');
if (result.success) {
  console.log('File data:', result.data);
}
```

### `deleteFromR2(key)`
Deletes a file from R2 bucket.

```typescript
const result = await deleteFromR2('uploads/123_abc_file.csv');
```

### `listR2Files(prefix?)`
Lists all files in bucket (for debugging).

```typescript
const result = await listR2Files('uploads/');
console.log('Files:', result.files);
```

## Testing R2 Integration

### Local Testing

1. Ensure `.env.local` has R2 credentials
2. Start dev server: `npm run dev`
3. Login as admin: `http://localhost:3000/login`
4. Navigate to File Manager
5. Upload a test file (e.g., `/tmp/test_leads.csv`)
6. Verify file appears in list
7. Click download and check file is retrieved
8. Delete file and confirm it's removed

### Test File

A test CSV file is available at `/tmp/test_leads.csv`:

```csv
name,phone,email,source
John Doe,+994501234567,john@example.com,villa.az
Jane Smith,+994551234567,jane@example.com,bul.az
Test User,+994701234567,test@example.com,direct
```

### Vercel Deployment

1. Add R2 environment variables to Vercel:
   - Go to **Settings** → **Environment Variables**
   - Add `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`

2. Push code to GitHub (already done):
   ```bash
   git push origin master
   ```

3. Vercel will auto-deploy with R2 storage

4. Test in production:
   - Login as admin
   - Upload files
   - Download files
   - Verify persistence across deployments

## Monitoring R2 Storage

### Check Bucket Usage

Login to Cloudflare Dashboard:
- Navigate to **R2** → **leadgenerator**
- View **Bucket Size** and operation counts
- Monitor Class A/B operations

### Database Queries

```sql
-- List all files in R2
SELECT id, original_filename, file_size, file_path, created_at
FROM leads.files
ORDER BY created_at DESC;

-- Total storage used
SELECT
    COUNT(*) as total_files,
    pg_size_pretty(SUM(file_size)::bigint) as total_size
FROM leads.files;

-- Files by type
SELECT
    file_type,
    COUNT(*) as count,
    pg_size_pretty(SUM(file_size)::bigint) as size
FROM leads.files
GROUP BY file_type;
```

## Cost Estimation

### R2 Pricing
- **Storage:** $0.015/GB/month
- **Class A Operations (write):** $4.50/million requests
- **Class B Operations (read):** $0.36/million requests
- **Egress:** **$0** (FREE!)

### Example Usage
- 1,000 files @ 1MB each = 1GB storage
- **Cost:** $0.015/month + negligible API costs
- **Downloads:** Unlimited at $0

### Comparison
- **AWS S3:** $0.023/GB + $0.09/GB egress
- **R2:** $0.015/GB + $0 egress
- **Savings:** ~40% on storage + 100% on bandwidth

## Troubleshooting

### Issue: "Error uploading to R2"

**Solution:**
1. Check R2 credentials in `.env.local`
2. Verify bucket name is correct
3. Check R2 bucket permissions in Cloudflare dashboard
4. View server logs: `npm run dev` output

### Issue: "File not found on R2"

**Solution:**
1. Check if file exists in R2 bucket (Cloudflare dashboard)
2. Verify `file_path` in database matches R2 key
3. Check R2 access permissions

### Issue: "403 Forbidden"

**Solution:**
- R2 Access Key ID or Secret Access Key is incorrect
- Update credentials in Vercel environment variables

## Migration from Local Storage

If you have existing files in `/uploads` directory:

### Option 1: Manual Upload
1. Download files from local `/uploads`
2. Re-upload through File Manager UI
3. Files will automatically go to R2

### Option 2: Migration Script
```bash
# Create migration script
node scripts/migrate_to_r2.js
```

Note: Since this is a new feature, you likely don't have old files to migrate.

## Security

✅ **Private by Default** - R2 bucket has public access disabled
✅ **Authenticated Downloads** - All downloads require login
✅ **Admin-Only Uploads** - Only admins can upload files
✅ **Encrypted in Transit** - HTTPS/TLS for all transfers
✅ **Access Control** - R2 API keys are environment-specific

## Next Steps

1. ✅ **R2 Integration Complete** - Files now stored in R2
2. ⏭️ **Deploy to Vercel** - Add R2 env vars and deploy
3. ⏭️ **Test in Production** - Upload/download files
4. ⏭️ **Monitor Usage** - Check R2 dashboard

## Support

If you encounter issues:

1. Check server logs in terminal
2. Check browser console (F12)
3. Verify R2 credentials
4. Check Cloudflare R2 dashboard for errors

---

**Built with:**
- Cloudflare R2 Storage
- AWS SDK for JavaScript v3
- Next.js 14 (App Router)
- PostgreSQL for metadata
