export default function HomePage() {
  return (
    <main className="grid gap-4 md:grid-cols-3">
      <section className="panel p-4">
        <h2 className="text-xl font-medium">Tenant Operations</h2>
        <p className="text-sm text-slate-200">Document ingestion, review queues, and status tracking.</p>
      </section>
      <section className="panel p-4">
        <h2 className="text-xl font-medium">Compliance</h2>
        <p className="text-sm text-slate-200">AECA, AVIQM, and DG workflows with auditable outcomes.</p>
      </section>
      <section className="panel p-4">
        <h2 className="text-xl font-medium">Analytics</h2>
        <p className="text-sm text-slate-200">Throughput, bottlenecks, discrepancy trends, and SLA risk.</p>
      </section>
    </main>
  );
}
