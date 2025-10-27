/**
 * API route for file downloads
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';

export const dynamic = 'force-dynamic';

/**
 * GET /api/files/download - Download a file
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
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ error: 'File ID is required' }, { status: 400 });
    }

    // Get file info from database
    const query = 'SELECT * FROM leads.files WHERE id = $1';
    const result = await pool.query(query, [id]);

    if (result.rows.length === 0) {
      return NextResponse.json({ error: 'File not found' }, { status: 404 });
    }

    const file = result.rows[0];

    // Check if file exists on disk
    if (!existsSync(file.file_path)) {
      return NextResponse.json({ error: 'File not found on server' }, { status: 404 });
    }

    // Increment download count
    await pool.query(
      'UPDATE leads.files SET download_count = download_count + 1 WHERE id = $1',
      [id]
    );

    // Read file from disk
    const fileBuffer = await readFile(file.file_path);

    // Set appropriate headers for download
    const headers = new Headers();
    headers.set('Content-Type', getContentType(file.file_type));
    headers.set('Content-Disposition', `attachment; filename="${file.original_filename}"`);
    headers.set('Content-Length', file.file_size.toString());

    return new NextResponse(fileBuffer, {
      status: 200,
      headers,
    });
  } catch (error) {
    console.error('Error downloading file:', error);
    return NextResponse.json({ error: 'Failed to download file' }, { status: 500 });
  }
}

/**
 * Helper function to get content type based on file extension
 */
function getContentType(fileType: string): string {
  const types: { [key: string]: string } = {
    csv: 'text/csv',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    xls: 'application/vnd.ms-excel',
    json: 'application/json',
    txt: 'text/plain',
  };

  return types[fileType] || 'application/octet-stream';
}
