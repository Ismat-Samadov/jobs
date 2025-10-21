/**
 * API route for dashboard statistics
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';

/**
 * GET /api/stats - Get dashboard statistics
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

    // Get various statistics
    const [totalLeads, leadsToday, leadsThisWeek, leadsThisMonth] = await Promise.all([
      pool.query('SELECT COUNT(*) as count FROM leads.leads'),
      pool.query('SELECT COUNT(*) as count FROM leads.leads WHERE created_at::date = CURRENT_DATE'),
      pool.query('SELECT COUNT(*) as count FROM leads.leads WHERE created_at >= CURRENT_DATE - INTERVAL \'7 days\''),
      pool.query('SELECT COUNT(*) as count FROM leads.leads WHERE created_at >= CURRENT_DATE - INTERVAL \'30 days\''),
    ]);

    // Get leads by source
    const leadsBySource = await pool.query(`
      SELECT
        website as source,
        COUNT(*) as count
      FROM leads.leads
      GROUP BY website
      ORDER BY count DESC
    `);

    // Get recent scraping activity (last 7 days)
    const recentActivity = await pool.query(`
      SELECT
        DATE(created_at) as date,
        COUNT(*) as count
      FROM leads.leads
      WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
      GROUP BY DATE(created_at)
      ORDER BY date DESC
    `);

    return NextResponse.json({
      totalLeads: parseInt(totalLeads.rows[0].count),
      leadsToday: parseInt(leadsToday.rows[0].count),
      leadsThisWeek: parseInt(leadsThisWeek.rows[0].count),
      leadsThisMonth: parseInt(leadsThisMonth.rows[0].count),
      leadsBySource: leadsBySource.rows,
      recentActivity: recentActivity.rows,
    });
  } catch (error) {
    console.error('Error fetching stats:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
