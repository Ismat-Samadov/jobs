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
      dataQualityResult,
      hourlyDistributionResult,
      weekdayDistributionResult,
      uniquePhoneNumbersResult,
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

      // Data quality metrics - leads with full_data vs without
      pool.query(`
        SELECT
          CASE
            WHEN full_data IS NOT NULL AND full_data::text != 'null' THEN 'Complete Data'
            ELSE 'Basic Data Only'
          END as data_status,
          COUNT(*) as count
        FROM leads.leads
        GROUP BY data_status
      `),

      // Hourly distribution - when are leads collected?
      pool.query(`
        SELECT
          EXTRACT(HOUR FROM created_at) as hour,
          COUNT(*) as count
        FROM leads.leads
        GROUP BY EXTRACT(HOUR FROM created_at)
        ORDER BY hour
      `),

      // Day of week distribution
      pool.query(`
        SELECT
          TO_CHAR(created_at, 'Day') as day_name,
          EXTRACT(DOW FROM created_at) as day_num,
          COUNT(*) as count
        FROM leads.leads
        GROUP BY day_name, day_num
        ORDER BY day_num
      `),

      // Unique phone numbers vs total leads
      pool.query(`
        SELECT
          COUNT(DISTINCT phone_number) as unique_phones,
          COUNT(*) as total_leads
        FROM leads.leads
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
    const dataQuality = dataQualityResult.rows;
    const hourlyDistribution = hourlyDistributionResult.rows;
    const weekdayDistribution = weekdayDistributionResult.rows;
    const phoneStats = uniquePhoneNumbersResult.rows[0];
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

    // Calculate data quality percentage
    const completeDataCount = dataQuality.find(row => row.data_status === 'Complete Data')?.count || 0;
    const dataQualityPercentage = totalLeads > 0
      ? ((parseInt(completeDataCount) / totalLeads) * 100).toFixed(1)
      : 0;

    // Calculate duplicate rate
    const duplicateRate = phoneStats.total_leads > 0
      ? (((parseInt(phoneStats.total_leads) - parseInt(phoneStats.unique_phones)) / parseInt(phoneStats.total_leads)) * 100).toFixed(1)
      : 0;

    return NextResponse.json({
      overview: {
        totalLeads,
        todayLeads,
        avgDailyLeads,
        growthPercentage,
        uniquePhones: parseInt(phoneStats.unique_phones),
        duplicateRate,
        dataQualityPercentage,
      },
      leadsBySource,
      topSources,
      leadsByDate,
      leadsLast30Days,
      dataQuality,
      hourlyDistribution,
      weekdayDistribution,
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
