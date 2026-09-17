import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Pill,
  ArrowRightLeft,
  AlertTriangle,
  ClipboardList,
  FileSpreadsheet,
  Clock,
  LogOut,
  LogIn,
} from 'lucide-react';

export default function Sidebar() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();

  return (
    <aside className="sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="sidebar-brand">
        <h1>PharmaFlow</h1>
        <div className="subtitle">Expiry-Aware Inventory</div>
      </div>
      <nav className="sidebar-nav" style={{ flex: 1 }}>
        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <LayoutDashboard />
          <span>Dashboard</span>
        </NavLink>
        <NavLink
          to="/medicines"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Pill />
          <span>Medicines</span>
        </NavLink>
        <NavLink
          to="/dispense"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <ArrowRightLeft />
          <span>Dispense</span>
        </NavLink>
        <NavLink
          to="/alerts"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <AlertTriangle />
          <span>Expiry Alerts</span>
        </NavLink>
        <NavLink
          to="/import"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <FileSpreadsheet />
          <span>Import Batches</span>
        </NavLink>
        <NavLink
          to="/automation"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Clock />
          <span>Clock & Outbox</span>
        </NavLink>
        <NavLink
          to="/transactions"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <ClipboardList />
          <span>Transactions</span>
        </NavLink>
      </nav>

      {/* User profile footer */}
      <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: isAdmin ? '#dc2626' : 'var(--primary-color)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.85rem',
                fontWeight: 700,
              }}>
                {user.username.charAt(0).toUpperCase()}
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{user.username}</div>
                <span className={`badge ${isAdmin ? 'badge-critical' : 'badge-healthy'}`} style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                  {user.role}
                </span>
              </div>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '6px' }}
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <Link to="/login" className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.85rem' }}>
            <LogIn size={14} />
            Sign In / Register
          </Link>
        )}
      </div>
    </aside>
  );
}
