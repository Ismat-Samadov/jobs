/**
 * NextAuth configuration
 */
import { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { getUserByUsername, verifyPassword, updateLastLogin } from '@/lib/auth';

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        username: { label: 'Username', type: 'text' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        console.log('🔐 Login attempt:', { username: credentials?.username });

        if (!credentials?.username || !credentials?.password) {
          console.log('❌ Missing credentials');
          throw new Error('Username and password required');
        }

        const user = await getUserByUsername(credentials.username);
        console.log('👤 User lookup:', user ? `Found: ${user.username}` : 'Not found');

        if (!user) {
          console.log('❌ User not found');
          throw new Error('Invalid username or password');
        }

        if (!user.is_active) {
          console.log('❌ Account disabled');
          throw new Error('Account is disabled');
        }

        console.log('🔑 Verifying password...');
        const isValid = await verifyPassword(credentials.password, user.password_hash);
        console.log('🔑 Password valid:', isValid);

        if (!isValid) {
          console.log('❌ Invalid password');
          throw new Error('Invalid username or password');
        }

        // Update last login
        await updateLastLogin(user.id);

        console.log('✅ Login successful:', user.username);
        return {
          id: user.id.toString(),
          name: user.username,
          email: user.username, // NextAuth requires email
          role: user.role,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        console.log('🔑 JWT callback - Setting role in token:', (user as any).role);
        token.role = (user as any).role;
        token.userId = user.id;
      }
      console.log('🔑 JWT callback - Token:', { role: token.role, userId: token.userId });
      return token;
    },
    async session({ session, token }) {
      console.log('📋 Session callback - Token role:', token.role);
      if (session.user) {
        (session.user as any).role = token.role;
        (session.user as any).id = token.userId;
      }
      console.log('📋 Session callback - Session user:', session.user);
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },
  secret: process.env.NEXTAUTH_SECRET,
};
