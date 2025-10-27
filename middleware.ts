/**
 * Middleware for protecting routes
 */
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';

export async function middleware(request: NextRequest) {
  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
  });

  const { pathname } = request.nextUrl;

  // Public routes
  if (pathname === '/' || pathname === '/login' || pathname.startsWith('/api/auth')) {
    // If user is logged in and trying to access login, redirect based on role
    if (token && pathname === '/login') {
      const userRole = (token as any).role;
      console.log('🔐 User logged in, redirecting from /login. Role:', userRole);
      if (userRole === 'admin') {
        return NextResponse.redirect(new URL('/admin', request.url));
      }
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
    return NextResponse.next();
  }

  // API routes handle their own authentication - let them through
  if (pathname.startsWith('/api/')) {
    return NextResponse.next();
  }

  // Protected routes - require authentication
  if (!token) {
    console.log('❌ No token found, redirecting to login from:', pathname);
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Admin-only routes
  if (pathname.startsWith('/admin') || pathname.startsWith('/file-manager')) {
    const userRole = (token as any).role;
    console.log('🔍 Admin route access attempt. Path:', pathname, 'Role:', userRole);
    if (userRole !== 'admin') {
      console.log('⛔ Access denied to admin route. Role:', userRole);
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
    console.log('✅ Admin access granted');
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, icons, images (static assets)
     * - manifest.json
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)|manifest.json).*)',
  ],
};
