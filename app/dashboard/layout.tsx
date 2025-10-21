import Providers from '../providers';
import Navbar from '@/components/Navbar';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main>{children}</main>
      </div>
    </Providers>
  );
}
