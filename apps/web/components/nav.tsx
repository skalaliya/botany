import Link from "next/link";

const links = [
  ["Home", "/"],
  ["Documents", "/documents"],
  ["Review", "/review"],
  ["AWB", "/dashboards/awb"],
  ["FIAR", "/dashboards/fiar"],
  ["AECA", "/dashboards/aeca"],
  ["AVIQM", "/dashboards/aviqm"],
  ["Station", "/dashboards/station-analytics"],
];

export default function Nav() {
  return (
    <nav className="flex flex-wrap gap-3 p-4 panel">
      {links.map(([label, href]) => (
        <Link key={href} href={href} className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-sm">
          {label}
        </Link>
      ))}
    </nav>
  );
}
