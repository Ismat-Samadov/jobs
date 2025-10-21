/**
 * Type definitions for NextAuth
 */
import 'next-auth';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      name: string;
      email: string;
      role: 'admin' | 'user';
    };
  }

  interface User {
    role: 'admin' | 'user';
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    role: 'admin' | 'user';
    userId: string;
  }
}
