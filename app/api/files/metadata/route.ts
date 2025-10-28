/**
 * Save file metadata after direct R2 upload
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';
import path from 'path';

export const dynamic = 'force-dynamic';

/**
 * POST /api/files/metadata - Save file metadata after direct upload (Admin only)
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

    const body = await request.json();
    const { key, originalFilename, fileSize, folderId, description } = body;

    if (!key || !originalFilename || !fileSize) {
      return NextResponse.json(
        { error: 'Key, originalFilename, and fileSize are required' },
        { status: 400 }
      );
    }

    const fileExt = path.extname(originalFilename).toLowerCase().replace('.', '');

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
      key, // Store R2 key as filename
      originalFilename,
      fileExt,
      fileSize,
      key, // Store R2 key as file_path
      folderId && folderId !== 'root' ? parseInt(folderId) : null,
      token.sub, // user id
      description || null,
    ];

    const result = await pool.query(insertQuery, values);

    return NextResponse.json({
      message: 'File metadata saved successfully',
      file: result.rows[0],
    });
  } catch (error) {
    console.error('Error saving file metadata:', error);
    return NextResponse.json(
      { error: 'Failed to save file metadata' },
      { status: 500 }
    );
  }
}
