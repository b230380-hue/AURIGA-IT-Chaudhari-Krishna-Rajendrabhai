import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Pill,
  ArrowRightLeft,
  AlertTriangle,
  ClipboardList,
  FileSpreadsheet,
  Clock,
} from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>PharmaFlow</h1>
        <div className="subtitle">Expiry-Aware Inventory</div>
      </div>
      <nav className="sidebar-nav">
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
    </aside>
  );
}
