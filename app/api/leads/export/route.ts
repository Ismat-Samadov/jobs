/**
 * API route for exporting leads to Excel
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';
import * as XLSX from 'xlsx';

/**
 * GET /api/leads/export - Export all leads to Excel
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

    // Get all leads
    const result = await pool.query(`
      SELECT
        id,
        phone_number,
        source_url,
        scraped_at
      FROM leads
      ORDER BY scraped_at DESC
    `);

    // Format data for Excel
    const data = result.rows.map(row => ({
      'ID': row.id,
      'Phone Number': row.phone_number,
      'Source URL': row.source_url,
      'Scraped At': new Date(row.scraped_at).toLocaleString(),
    }));

    // Create workbook and worksheet
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(data);

    // Set column widths
    worksheet['!cols'] = [
      { wch: 8 },   // ID
      { wch: 15 },  // Phone Number
      { wch: 50 },  // Source URL
      { wch: 20 },  // Scraped At
    ];

    XLSX.utils.book_append_sheet(workbook, worksheet, 'Leads');

    // Generate buffer
    const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });

    // Return as downloadable file
    const filename = `leads_export_${new Date().toISOString().split('T')[0]}.xlsx`;

    return new NextResponse(buffer, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Error exporting leads:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
