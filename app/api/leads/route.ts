/**
 * API routes for leads data
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';

export const dynamic = 'force-dynamic';

export interface Lead {
  id: number;
  phone_number: string;
  website: string;
  source: string;
  created_at: string;
  full_data?: any; // JSON data with full listing details
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
    const website = searchParams.get('website') || '';
    const dateFrom = searchParams.get('dateFrom') || '';
    const dateTo = searchParams.get('dateTo') || '';
    const sortBy = searchParams.get('sortBy') || 'created_at';
    const sortOrder = searchParams.get('sortOrder') || 'DESC';

    const offset = (page - 1) * limit;

    // Build query with filters
    let query = `
      SELECT id, phone_number, website, source, created_at, full_data
      FROM leads.leads
    `;

    const queryParams: any[] = [];
    const whereConditions: string[] = [];
    let paramIndex = 1;

    if (search) {
      whereConditions.push(`(phone_number LIKE $${paramIndex} OR source LIKE $${paramIndex})`);
      queryParams.push(`%${search}%`);
      paramIndex++;
    }

    if (website && website !== 'all') {
      whereConditions.push(`website = $${paramIndex}`);
      queryParams.push(website);
      paramIndex++;
    }

    if (dateFrom) {
      whereConditions.push(`created_at >= $${paramIndex}`);
      queryParams.push(dateFrom);
      paramIndex++;
    }

    if (dateTo) {
      whereConditions.push(`created_at <= $${paramIndex}`);
      queryParams.push(dateTo + ' 23:59:59'); // Include full day
      paramIndex++;
    }

    if (whereConditions.length > 0) {
      query += ` WHERE ${whereConditions.join(' AND ')}`;
    }

    // Validate sortBy to prevent SQL injection
    const allowedSortFields = ['id', 'phone_number', 'created_at', 'website'];
    const validSortBy = allowedSortFields.includes(sortBy) ? sortBy : 'created_at';
    const validSortOrder = sortOrder.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';

    query += ` ORDER BY ${validSortBy} ${validSortOrder}`;
    query += ` LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`;
    queryParams.push(limit, offset);

    // Get total count with same filters
    let countQuery = 'SELECT COUNT(*) as total FROM leads.leads';
    const countParams: any[] = [];
    const countWhereConditions: string[] = [];
    let countParamIndex = 1;

    if (search) {
      countWhereConditions.push(`(phone_number LIKE $${countParamIndex} OR source LIKE $${countParamIndex})`);
      countParams.push(`%${search}%`);
      countParamIndex++;
    }

    if (website && website !== 'all') {
      countWhereConditions.push(`website = $${countParamIndex}`);
      countParams.push(website);
      countParamIndex++;
    }

    if (dateFrom) {
      countWhereConditions.push(`created_at >= $${countParamIndex}`);
      countParams.push(dateFrom);
      countParamIndex++;
    }

    if (dateTo) {
      countWhereConditions.push(`created_at <= $${countParamIndex}`);
      countParams.push(dateTo + ' 23:59:59');
      countParamIndex++;
    }

    if (countWhereConditions.length > 0) {
      countQuery += ` WHERE ${countWhereConditions.join(' AND ')}`;
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
