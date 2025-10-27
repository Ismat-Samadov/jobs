/**
 * API routes for file operations with Cloudflare R2 storage
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';
import { uploadToR2, deleteFromR2, getContentType, generateR2Key } from '@/lib/r2';
import path from 'path';

export const dynamic = 'force-dynamic';

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

        // Generate unique R2 key
        const r2Key = generateR2Key(file.name);
        const contentType = getContentType(fileExt.replace('.', ''));

        // Upload file to R2
        const bytes = await file.arrayBuffer();
        const buffer = Buffer.from(bytes);
        const uploadResult = await uploadToR2(r2Key, buffer, contentType);

        if (!uploadResult.success) {
          results.failed.push({
            filename: file.name,
            error: uploadResult.error || 'R2 upload failed',
          });
          continue;
        }

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
          r2Key, // Store R2 key as filename
          file.name,
          fileExt.replace('.', ''),
          file.size,
          r2Key, // Store R2 key as file_path
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

    // Delete file from R2
    const deleteResult = await deleteFromR2(file.file_path);
    if (!deleteResult.success) {
      console.error('Error deleting file from R2:', deleteResult.error);
      // Continue anyway to clean up database
    }

    // Delete from database
    await pool.query('DELETE FROM leads.files WHERE id = $1', [id]);

    return NextResponse.json({ message: 'File deleted successfully' });
  } catch (error) {
    console.error('Error deleting file:', error);
    return NextResponse.json({ error: 'Failed to delete file' }, { status: 500 });
  }
}
