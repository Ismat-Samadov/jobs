/**
 * API routes for file operations
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';
import { writeFile, unlink, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

const UPLOAD_DIR = path.join(process.cwd(), 'uploads');

// Ensure upload directory exists
async function ensureUploadDir() {
  if (!existsSync(UPLOAD_DIR)) {
    await mkdir(UPLOAD_DIR, { recursive: true });
  }
}

/**
 * GET /api/files - Get all files with optional folder filter
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const folderId = searchParams.get('folderId');

    let query = `
      SELECT
        f.id,
        f.filename,
        f.original_filename,
        f.file_type,
        f.file_size,
        f.folder_id,
        f.description,
        f.download_count,
        f.created_at,
        f.updated_at,
        u.username as uploaded_by,
        folder.name as folder_name
      FROM leads.files f
      LEFT JOIN users u ON f.uploaded_by = u.id
      LEFT JOIN leads.folders folder ON f.folder_id = folder.id
    `;

    const params: any[] = [];

    if (folderId) {
      if (folderId === 'root') {
        query += ' WHERE f.folder_id IS NULL';
      } else {
        query += ' WHERE f.folder_id = $1';
        params.push(parseInt(folderId));
      }
    }

    query += ' ORDER BY f.created_at DESC';

    const result = await pool.query(query, params);

    return NextResponse.json({ files: result.rows });
  } catch (error) {
    console.error('Error fetching files:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

/**
 * POST /api/files - Upload file(s) (Admin only)
 * Supports single file or bulk upload
 */
export async function POST(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || token.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    await ensureUploadDir();

    const formData = await request.formData();
    const files = formData.getAll('files') as File[];
    const folderId = formData.get('folderId') as string;
    const description = formData.get('description') as string;

    if (!files || files.length === 0) {
      return NextResponse.json({ error: 'No files provided' }, { status: 400 });
    }

    // Validate file types
    const allowedTypes = ['.csv', '.xlsx', '.xls', '.json', '.txt'];
    const results = {
      uploaded: [] as any[],
      failed: [] as { filename: string; error: string }[],
      total: files.length,
    };

    for (const file of files) {
      try {
        const fileExt = path.extname(file.name).toLowerCase();

        if (!allowedTypes.includes(fileExt)) {
          results.failed.push({
            filename: file.name,
            error: `Invalid file type. Allowed: ${allowedTypes.join(', ')}`,
          });
          continue;
        }

        // Generate unique filename
        const timestamp = Date.now();
        const randomSuffix = Math.random().toString(36).substring(2, 8);
        const sanitizedName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
        const filename = `${timestamp}_${randomSuffix}_${sanitizedName}`;
        const filePath = path.join(UPLOAD_DIR, filename);

        // Save file to disk
        const bytes = await file.arrayBuffer();
        const buffer = Buffer.from(bytes);
        await writeFile(filePath, buffer);

        // Save file metadata to database
        const insertQuery = `
          INSERT INTO leads.files (
            filename,
            original_filename,
            file_type,
            file_size,
            file_path,
            folder_id,
            uploaded_by,
            description
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
          RETURNING *
        `;

        const values = [
          filename,
          file.name,
          fileExt.replace('.', ''),
          file.size,
          filePath,
          folderId && folderId !== 'root' ? parseInt(folderId) : null,
          token.sub, // user id
          description || null,
        ];

        const result = await pool.query(insertQuery, values);
        results.uploaded.push(result.rows[0]);
      } catch (error: any) {
        console.error(`Error uploading file ${file.name}:`, error);
        results.failed.push({
          filename: file.name,
          error: error.message || 'Upload failed',
        });
      }
    }

    // Return response based on results
    if (results.uploaded.length === 0) {
      return NextResponse.json(
        {
          error: 'All files failed to upload',
          details: results.failed,
        },
        { status: 400 }
      );
    }

    if (results.failed.length > 0) {
      return NextResponse.json({
        message: `${results.uploaded.length} file(s) uploaded, ${results.failed.length} failed`,
        uploaded: results.uploaded,
        failed: results.failed,
        total: results.total,
      });
    }

    return NextResponse.json({
      message: `${results.uploaded.length} file(s) uploaded successfully`,
      uploaded: results.uploaded,
      total: results.total,
    });
  } catch (error) {
    console.error('Error uploading files:', error);
    return NextResponse.json({ error: 'Failed to upload files' }, { status: 500 });
  }
}

/**
 * PUT /api/files - Update file metadata (Admin only)
 */
export async function PUT(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || token.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { id, original_filename, description, folder_id } = body;

    if (!id) {
      return NextResponse.json({ error: 'File ID is required' }, { status: 400 });
    }

    const updateQuery = `
      UPDATE leads.files
      SET
        original_filename = COALESCE($1, original_filename),
        description = COALESCE($2, description),
        folder_id = $3
      WHERE id = $4
      RETURNING *
    `;

    const values = [
      original_filename,
      description,
      folder_id && folder_id !== 'root' ? parseInt(folder_id) : null,
      id,
    ];

    const result = await pool.query(updateQuery, values);

    if (result.rows.length === 0) {
      return NextResponse.json({ error: 'File not found' }, { status: 404 });
    }

    return NextResponse.json({
      message: 'File updated successfully',
      file: result.rows[0],
    });
  } catch (error) {
    console.error('Error updating file:', error);
    return NextResponse.json({ error: 'Failed to update file' }, { status: 500 });
  }
}

/**
 * DELETE /api/files - Delete a file (Admin only)
 */
export async function DELETE(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || token.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ error: 'File ID is required' }, { status: 400 });
    }

    // Get file info
    const fileQuery = 'SELECT * FROM leads.files WHERE id = $1';
    const fileResult = await pool.query(fileQuery, [id]);

    if (fileResult.rows.length === 0) {
      return NextResponse.json({ error: 'File not found' }, { status: 404 });
    }

    const file = fileResult.rows[0];

    // Delete file from disk
    try {
      if (existsSync(file.file_path)) {
        await unlink(file.file_path);
      }
    } catch (err) {
      console.error('Error deleting file from disk:', err);
    }

    // Delete from database
    await pool.query('DELETE FROM leads.files WHERE id = $1', [id]);

    return NextResponse.json({ message: 'File deleted successfully' });
  } catch (error) {
    console.error('Error deleting file:', error);
    return NextResponse.json({ error: 'Failed to delete file' }, { status: 500 });
  }
}
