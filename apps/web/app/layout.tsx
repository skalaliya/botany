import "./globals.css";
import Nav from "../components/nav";

export const metadata = {
  title: "NexusCargo Platform",
  description: "Unified multi-tenant logistics AI SaaS",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          <h1 className="text-3xl font-semibold">NexusCargo AI Platform</h1>
          <Nav />
          {children}
        </div>
      </body>
    </html>
  );
}
