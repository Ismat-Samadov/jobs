/**
 * API route for exporting leads to Excel
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';

export const dynamic = 'force-dynamic';

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

    // Get total count first
    const countResult = await pool.query('SELECT COUNT(*) FROM leads.leads');
    const totalLeads = parseInt(countResult.rows[0].count);

    // Return JSON data for client-side Excel generation
    // This avoids Vercel's 4.5MB response limit by using streaming
    const EXPORT_LIMIT = 10000;
    let query = `
      SELECT
        id,
        phone_number,
        website,
        source,
        created_at,
        full_data
      FROM leads.leads
      ORDER BY created_at DESC
    `;

    if (totalLeads > EXPORT_LIMIT) {
      query += ` LIMIT ${EXPORT_LIMIT}`;
      console.log(`Limiting export to ${EXPORT_LIMIT} most recent leads (total: ${totalLeads})`);
    }

    // Get leads with limit
    const result = await pool.query(query);

    // Return raw data as JSON for client-side processing
    return NextResponse.json({
      success: true,
      totalLeads,
      exportedLeads: result.rows.length,
      data: result.rows,
    });
  } catch (error) {
    console.error('Error exporting leads:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
