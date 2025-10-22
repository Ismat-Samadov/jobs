import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/nextauth';
import pool from '@/lib/db';

// Force dynamic rendering for this route
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const session = await getServerSession(authOptions);

    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Fetch comprehensive analytics data
    const [
      totalLeadsResult,
      leadsBySourceResult,
      leadsByDateResult,
      leadsLast30DaysResult,
      topCitiesResult,
      topSubjectsResult,
      websiteGrowthResult,
      dailyGrowthResult,
    ] = await Promise.all([
      // Total leads count
      pool.query('SELECT COUNT(*) as total FROM leads.leads'),

      // Leads by source (website)
      pool.query(`
        SELECT website, COUNT(*) as count
        FROM leads.leads
        GROUP BY website
        ORDER BY count DESC
      `),

      // Leads by date (last 7 days)
      pool.query(`
        SELECT
          DATE(created_at) as date,
          COUNT(*) as count
        FROM leads.leads
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
      `),

      // Leads created in last 30 days
      pool.query(`
        SELECT
          DATE(created_at) as date,
          COUNT(*) as count
        FROM leads.leads
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date ASC
      `),

      // Top cities (from tutors data)
      pool.query(`
        SELECT
          full_data->>'city' as city,
          COUNT(*) as count
        FROM leads.leads
        WHERE full_data->>'city' IS NOT NULL
        AND full_data->>'city' != ''
        GROUP BY full_data->>'city'
        ORDER BY count DESC
        LIMIT 10
      `),

      // Top subjects (from tutors data)
      pool.query(`
        SELECT
          full_data->>'subject_taught' as subject,
          COUNT(*) as count
        FROM leads.leads
        WHERE full_data->>'subject_taught' IS NOT NULL
        AND full_data->>'subject_taught' != ''
        GROUP BY full_data->>'subject_taught'
        ORDER BY count DESC
        LIMIT 10
      `),

      // Website growth over time
      pool.query(`
        SELECT
          website,
          DATE(created_at) as date,
          COUNT(*) as count
        FROM leads.leads
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY website, DATE(created_at)
        ORDER BY date ASC, website
      `),

      // Daily growth rate
      pool.query(`
        SELECT
          DATE(created_at) as date,
          COUNT(*) as count,
          COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY DATE(created_at)) as growth
        FROM leads.leads
        WHERE created_at >= NOW() - INTERVAL '14 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
      `),
    ]);

    // Calculate statistics
    const totalLeads = parseInt(totalLeadsResult.rows[0].total);
    const leadsBySource = leadsBySourceResult.rows;
    const leadsByDate = leadsByDateResult.rows;
    const leadsLast30Days = leadsLast30DaysResult.rows;
    const topCities = topCitiesResult.rows;
    const topSubjects = topSubjectsResult.rows;
    const websiteGrowth = websiteGrowthResult.rows;
    const dailyGrowth = dailyGrowthResult.rows;

    // Calculate growth percentages
    const todayLeads = leadsByDate.find(row => {
      const today = new Date().toISOString().split('T')[0];
      return row.date.toISOString().split('T')[0] === today;
    })?.count || 0;

    const yesterdayLeads = leadsByDate[1]?.count || 0;
    const growthPercentage = yesterdayLeads > 0
      ? ((todayLeads - yesterdayLeads) / yesterdayLeads * 100).toFixed(1)
      : 0;

    // Calculate average daily leads
    const avgDailyLeads = leadsLast30Days.length > 0
      ? Math.round(leadsLast30Days.reduce((sum, row) => sum + parseInt(row.count), 0) / leadsLast30Days.length)
      : 0;

    // Top 5 sources
    const topSources = leadsBySource.slice(0, 5);

    return NextResponse.json({
      overview: {
        totalLeads,
        todayLeads,
        avgDailyLeads,
        growthPercentage,
      },
      leadsBySource,
      topSources,
      leadsByDate,
      leadsLast30Days,
      topCities,
      topSubjects,
      websiteGrowth,
      dailyGrowth,
    });
  } catch (error) {
    console.error('Error fetching analytics:', error);
    return NextResponse.json(
      { error: 'Failed to fetch analytics' },
      { status: 500 }
    );
  }
}
