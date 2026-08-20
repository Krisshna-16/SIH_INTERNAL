import React from 'react';
import { NavLink, useParams } from 'react-router-dom';

interface NavGroup {
  groupLabel: string;
  items: { to: string; label: string; iconSvg: React.ReactNode }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    groupLabel: 'OVERVIEW',
    items: [
      {
        to: 'dashboard',
        label: 'Mission Control',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="9" />
            <rect x="14" y="3" width="7" height="5" />
            <rect x="14" y="12" width="7" height="9" />
            <rect x="3" y="16" width="7" height="5" />
          </svg>
        ),
      },
    ],
  },
  {
    groupLabel: 'DATA EXPLORER',
    items: [
      {
        to: 'entities',
        label: 'Neural Entities',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        ),
      },
      {
        to: 'evidence',
        label: 'Evidence Vault',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        ),
      },
    ],
  },
  {
    groupLabel: 'INTELLIGENCE & GRAPH',
    items: [
      {
        to: 'findings',
        label: 'Anomaly Findings',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
            <line x1="4" y1="22" x2="4" y2="15" />
          </svg>
        ),
      },
      {
        to: 'relationships',
        label: 'Derived Relations',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
        ),
      },
      {
        to: 'timeline',
        label: 'Timeline Stream',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        ),
      },
      {
        to: 'graph',
        label: 'Knowledge Graph',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
        ),
      },
    ],
  },
  {
    groupLabel: 'AI & AUDIT',
    items: [
      {
        to: 'chat',
        label: 'TRACE-X Co-Analyst',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        ),
      },
      {
        to: 'query',
        label: 'Structured Query',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
            <line x1="11" y1="8" x2="11" y2="14" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
        ),
      },
      {
        to: 'privacy',
        label: 'Privacy Gateway',
        iconSvg: (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        ),
      },
    ],
  },
];

export const Sidebar: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const basePath = `/reports/${reportId}`;

  return (
    <aside className="sidebar">
      {/* Brand Header without emojis */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon-box">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>
        <div className="sidebar-brand-text">
          <span className="brand-main">TRACE-X</span>
          <span className="brand-sub">INVESTIGATOR</span>
        </div>
      </div>

      {/* Navigation Links Grouped */}
      <nav className="sidebar-nav">
        {NAV_GROUPS.map((group, idx) => (
          <div key={idx} className="nav-group">
            <span className="nav-group-title">{group.groupLabel}</span>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={`${basePath}/${item.to}`}
                className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
              >
                <span className="sidebar-link-icon">{item.iconSvg}</span>
                <span className="sidebar-link-label">{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer Return Link */}
      <div className="sidebar-footer">
        <NavLink to="/" className="sidebar-link sidebar-back-link">
          <span className="sidebar-link-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          </span>
          <span className="sidebar-link-label">Select Case / Report</span>
        </NavLink>
      </div>
    </aside>
  );
};
