/**
 * API route for file downloads from Cloudflare R2
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';
import { downloadFromR2, getContentType } from '@/lib/r2';

export const dynamic = 'force-dynamic';

/**
 * GET /api/files/download - Download a file from R2
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

    // Download file from R2
    const downloadResult = await downloadFromR2(file.file_path);

    if (!downloadResult.success || !downloadResult.data) {
      return NextResponse.json(
        { error: downloadResult.error || 'File not found on R2' },
        { status: 404 }
      );
    }

    // Increment download count
    await pool.query(
      'UPDATE leads.files SET download_count = download_count + 1 WHERE id = $1',
      [id]
    );

    // Set appropriate headers for download
    const headers = new Headers();
    headers.set('Content-Type', downloadResult.contentType || getContentType(file.file_type));
    headers.set('Content-Disposition', `attachment; filename="${file.original_filename}"`);
    headers.set('Content-Length', downloadResult.data.length.toString());

    return new NextResponse(downloadResult.data, {
      status: 200,
      headers,
    });
  } catch (error) {
    console.error('Error downloading file:', error);
    return NextResponse.json({ error: 'Failed to download file' }, { status: 500 });
  }
}
