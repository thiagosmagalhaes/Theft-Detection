"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, History, Settings, ShieldAlert } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/history", label: "Alert History", icon: History },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside className="w-64 glass-panel border-l-0 rounded-l-none min-h-screen flex flex-col p-4">
      <div className="flex items-center gap-3 mb-10 px-2 mt-4">
        <ShieldAlert className="w-8 h-8 text-brand" />
        <h1 className="text-xl font-bold tracking-wider">
          <span className="text-brand">Theft</span>Guard
        </h1>
      </div>

      <nav className="flex-1 space-y-2">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href;

          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? "bg-brand/20 text-brand font-medium border border-brand/30 shadow-[0_0_15px_rgba(59,130,246,0.15)]"
                  : "text-foreground/70 hover:bg-glass hover:text-foreground"
              }`}
            >
              <Icon className="w-5 h-5" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-8 pb-4">
        <div className="px-4 py-3 rounded-lg bg-black/20 border border-glass-border">
          <div className="text-xs text-foreground/50 uppercase tracking-wider mb-1">System Status</div>
          <div className="flex items-center gap-2 text-sm text-green-400">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
            Online & Active
          </div>
        </div>
      </div>
    </aside>
  );
}
