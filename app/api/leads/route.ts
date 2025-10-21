/**
 * API routes for leads data
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';

export interface Lead {
  id: number;
  phone_number: string;
  source_url: string;
  scraped_at: string;
}

/**
 * GET /api/leads - Get all leads with pagination and filters
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
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '100');
    const search = searchParams.get('search') || '';
    const sortBy = searchParams.get('sortBy') || 'scraped_at';
    const sortOrder = searchParams.get('sortOrder') || 'DESC';

    const offset = (page - 1) * limit;

    // Build query with search filter
    let query = `
      SELECT id, phone_number, source_url, scraped_at
      FROM leads
    `;

    const queryParams: any[] = [];
    let paramIndex = 1;

    if (search) {
      query += ` WHERE phone_number LIKE $${paramIndex} OR source_url LIKE $${paramIndex}`;
      queryParams.push(`%${search}%`);
      paramIndex++;
    }

    // Validate sortBy to prevent SQL injection
    const allowedSortFields = ['id', 'phone_number', 'scraped_at'];
    const validSortBy = allowedSortFields.includes(sortBy) ? sortBy : 'scraped_at';
    const validSortOrder = sortOrder.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';

    query += ` ORDER BY ${validSortBy} ${validSortOrder}`;
    query += ` LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`;
    queryParams.push(limit, offset);

    // Get total count
    let countQuery = 'SELECT COUNT(*) as total FROM leads';
    const countParams: any[] = [];

    if (search) {
      countQuery += ' WHERE phone_number LIKE $1 OR source_url LIKE $1';
      countParams.push(`%${search}%`);
    }

    const [dataResult, countResult] = await Promise.all([
      pool.query(query, queryParams),
      pool.query(countQuery, countParams),
    ]);

    const total = parseInt(countResult.rows[0].total);
    const totalPages = Math.ceil(total / limit);

    return NextResponse.json({
      data: dataResult.rows,
      pagination: {
        page,
        limit,
        total,
        totalPages,
      },
    });
  } catch (error) {
    console.error('Error fetching leads:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
