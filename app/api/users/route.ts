/**
 * API routes for user management (Admin only)
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import { getAllUsers, createUser, updateUser, deleteUser } from '@/lib/auth';
import { z } from 'zod';

const createUserSchema = z.object({
  username: z.string().min(3).max(50),
  password: z.string().min(6),
  role: z.enum(['admin', 'user']),
});

const updateUserSchema = z.object({
  id: z.number(),
  username: z.string().min(3).max(50).optional(),
  password: z.string().min(6).optional(),
  is_active: z.boolean().optional(),
});

/**
 * GET /api/users - Get all users (Admin only)
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || (token as any).role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const users = await getAllUsers();
    return NextResponse.json(users);
  } catch (error) {
    console.error('Error fetching users:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

/**
 * POST /api/users - Create new user (Admin only)
 */
export async function POST(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || (token as any).role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const validated = createUserSchema.parse(body);

    const user = await createUser(
      validated.username,
      validated.password,
      validated.role,
      parseInt((token as any).userId)
    );

    return NextResponse.json(user, { status: 201 });
  } catch (error: any) {
    console.error('Error creating user:', error);

    if (error.name === 'ZodError') {
      return NextResponse.json({ error: 'Invalid input', details: error.errors }, { status: 400 });
    }

    if (error.code === '23505') {
      // Unique constraint violation
      return NextResponse.json({ error: 'Username already exists' }, { status: 409 });
    }

    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

/**
 * PUT /api/users - Update user (Admin only)
 */
export async function PUT(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || (token as any).role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const validated = updateUserSchema.parse(body);

    const { id, ...updates } = validated;
    const user = await updateUser(id, updates);

    return NextResponse.json(user);
  } catch (error: any) {
    console.error('Error updating user:', error);

    if (error.name === 'ZodError') {
      return NextResponse.json({ error: 'Invalid input', details: error.errors }, { status: 400 });
    }

    if (error.message === 'User not found') {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

/**
 * DELETE /api/users?id=1 - Delete user (Admin only)
 */
export async function DELETE(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || (token as any).role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ error: 'User ID required' }, { status: 400 });
    }

    await deleteUser(parseInt(id));

    return NextResponse.json({ message: 'User deleted successfully' });
  } catch (error: any) {
    console.error('Error deleting user:', error);

    if (error.message === 'User not found or cannot delete admin') {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
