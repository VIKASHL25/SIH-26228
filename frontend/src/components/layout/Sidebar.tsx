import React, { useState } from 'react';
import {
  LayoutDashboard,
  Database,
  Cpu,
  KeyRound,
  Compass,
  Users,
  ScrollText,
  Link2,
  SearchCode,
  FileCheck2,
  ShieldAlert,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useAssurance, NavigationTab } from '../../context/AssuranceContext';

interface NavItemConfig {
  id: NavigationTab;
  label: string;
  icon: React.ReactNode;
  badge?: number | string;
  badgeColor?: string;
}

export const Sidebar: React.FC = () => {
  const { activeTab, setActiveTab, report } = useAssurance();
  const [collapsed, setCollapsed] = useState(false);

  const findingsCount = report?.findings?.length || 0;
  const criticalCount = report?.summary_counts?.CRITICAL || 0;

  const navItems: NavItemConfig[] = [
    {
      id: 'overview',
      label: 'Assurance Overview',
      icon: <LayoutDashboard className="w-4 h-4" />
    },
    {
      id: 'data',
      label: 'Data Integrity',
      icon: <Database className="w-4 h-4" />
    },
    {
      id: 'model',
      label: 'Model Integrity',
      icon: <Cpu className="w-4 h-4" />
    },
    {
      id: 'inference',
      label: 'Inference Integrity',
      icon: <KeyRound className="w-4 h-4" />
    },
    {
      id: 'shift',
      label: 'Distribution Shift',
      icon: <Compass className="w-4 h-4" />
    },
    {
      id: 'contributors',
      label: 'Contributor Risk',
      icon: <Users className="w-4 h-4" />
    },
    {
      id: 'audit',
      label: 'Audit Trail',
      icon: <ScrollText className="w-4 h-4" />
    },
    {
      id: 'blockchain',
      label: 'Trust Ledger',
      icon: <Link2 className="w-4 h-4 text-amber-400" />,
      badge: 'Fabric',
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30'
    },
    {
      id: 'findings',
      label: 'Findings & Evidence',
      icon: <SearchCode className="w-4 h-4" />,
      badge: findingsCount > 0 ? findingsCount : undefined,
      badgeColor: criticalCount > 0 ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
    },
    {
      id: 'reports',
      label: 'Reports',
      icon: <FileCheck2 className="w-4 h-4" />
    },
    {
      id: 'coverage',
      label: 'System / Coverage',
      icon: <ShieldAlert className="w-4 h-4" />
    }
  ];

  return (
    <aside
      className={`bg-[#0a0f1d] border-r border-slate-800/80 flex flex-col justify-between transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="py-4">
        <div className="px-3 mb-2 flex items-center justify-between">
          {!collapsed && (
            <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-medium px-2">
              Forensics Engine
            </span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-md transition-colors mx-auto"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        <nav className="space-y-1 px-2">
          {navItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-950/70 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-950/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                }`}
                title={collapsed ? item.label : undefined}
              >
                <span className={isActive ? 'text-cyan-400' : 'text-slate-400'}>
                  {item.icon}
                </span>

                {!collapsed && (
                  <span className="flex-1 text-left tracking-wide truncate">
                    {item.label}
                  </span>
                )}

                {!collapsed && item.badge !== undefined && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      item.badgeColor || 'bg-slate-800 text-slate-300 border-slate-700'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Sidebar Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
        {!collapsed ? (
          <div className="text-[11px] text-slate-400 space-y-1">
            <div className="flex justify-between items-center">
              <span>Security Level:</span>
              <span className="text-emerald-400 font-mono">AIRGAP-E4</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Hash Algorithm:</span>
              <span className="text-cyan-300 font-mono">SHA-256</span>
            </div>
          </div>
        ) : (
          <div className="w-2 h-2 rounded-full bg-emerald-400 mx-auto" title="Air-gapped mode active"></div>
        )}
      </div>
    </aside>
  );
};
