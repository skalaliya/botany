export default function StationAnalyticsPage() {
  const cards = [
    { label: "Throughput / hr", value: "26.4", hint: "vs target 25.0" },
    { label: "Avg dwell (min)", value: "82", hint: "loading zone bottleneck" },
    { label: "SLA risk", value: "9.2%", hint: "amber threshold" },
    { label: "Delayed shipments", value: "31", hint: "rolling 24h" },
  ];

  return (
    <main className="space-y-6">
      <section className="panel p-6">
        <h1 className="text-2xl font-semibold">Station Analytics</h1>
        <p className="mt-2 text-sm text-slate-200">
          Throughput, bottleneck signals, and SLA risk insights powered by daily analytics transforms.
        </p>
      </section>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <article key={card.label} className="panel p-4">
            <p className="text-xs uppercase tracking-wide text-slate-300">{card.label}</p>
            <p className="mt-2 text-2xl font-semibold">{card.value}</p>
            <p className="mt-1 text-xs text-slate-300">{card.hint}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
