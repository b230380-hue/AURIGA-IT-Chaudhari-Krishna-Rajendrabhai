import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboard } from '../api/client';
import type { DashboardData } from '../types';
import { formatDate, daysText, getStatusBadgeClass, statusLabel } from '../utils/helpers';
import {
  Package,
  AlertTriangle,
  ShieldCheck,
  Clock,
  ArrowDown,
  CheckCircle,
  ClipboardList,
} from 'lucide-react';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => setError('Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /> Loading dashboard…</div>;
  if (error) return <div className="error-message"><strong>Error</strong>{error}</div>;
  if (!data) return null;

  const { summary, health, exposure, needs_attention, fefo_queue, recent_dispenses } = data;

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Pharmacy inventory overview — FEFO protected</p>
      </div>

      {/* Summary Cards */}
      <div className="summary-grid">
        <div className="summary-card success">
          <div className="label">Sellable Units</div>
          <div className="value">{summary.sellable_units.toLocaleString()}</div>
        </div>
        <div className="summary-card danger">
          <div className="label">Expired Units</div>
          <div className="value">{summary.expired_units.toLocaleString()}</div>
        </div>
        <div className="summary-card warning">
          <div className="label">Expiring Soon</div>
          <div className="value">{summary.expiring_soon_units.toLocaleString()}</div>
        </div>
        <div className="summary-card primary">
          <div className="label">Medicines Available</div>
          <div className="value">{summary.medicines_in_stock}</div>
        </div>
        <div className="summary-card">
          <div className="label">Attention Required</div>
          <div className="value">{summary.batches_requiring_attention}</div>
        </div>
      </div>

      {/* Health Score + Exposure */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)', marginBottom: 'var(--space-8)' }}>
        <div className="card">
          <div className="card-header">
            <h2>Inventory Health</h2>
          </div>
          <div className="health-indicator">
            <div className={`health-score grade-${health.grade.toLowerCase()}`}>
              {health.grade}
            </div>
            <div className="health-details">
              <div className="health-grade">Score: {health.score}/100</div>
              <div className="health-explanation">{health.explanation}</div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-2)', marginTop: 'var(--space-3)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
            <div><ShieldCheck size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />{health.sellable_percentage}% sellable</div>
            <div><AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />{health.expired_percentage}% expired</div>
            <div><Package size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />{health.total_physical_units} physical</div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>Potential Expiry Exposure</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)', marginTop: 'var(--space-2)' }}>
            <div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Within 7 Days</div>
              <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--color-danger)' }}>{exposure.units_expiring_within_7_days} units</div>
              {exposure.potential_value_at_risk_7d !== null && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Value at risk: ${exposure.potential_value_at_risk_7d.toFixed(2)}</div>
              )}
            </div>
            <div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Within 30 Days</div>
              <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--color-warning)' }}>{exposure.units_expiring_within_30_days} units</div>
              {exposure.potential_value_at_risk_30d !== null && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Value at risk: ${exposure.potential_value_at_risk_30d.toFixed(2)}</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Needs Attention + FEFO Queue */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)', marginBottom: 'var(--space-8)' }}>
        <div className="card">
          <div className="card-header">
            <h2>Needs Attention</h2>
            <button className="btn btn-outline btn-sm" onClick={() => navigate('/alerts')}>View All</button>
          </div>
          {needs_attention.length === 0 ? (
            <div className="empty-state" style={{ padding: 'var(--space-6)' }}>
              <CheckCircle size={32} />
              <h3>All Clear</h3>
              <p>No batches require immediate attention</p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Medicine</th>
                    <th>Batch</th>
                    <th>Qty</th>
                    <th>Status</th>
                    <th>Expiry</th>
                  </tr>
                </thead>
                <tbody>
                  {needs_attention.map((item) => (
                    <tr key={item.batch_id} className="clickable-row" onClick={() => navigate(`/medicines/${item.medicine_id}`)}>
                      <td style={{ fontWeight: 500 }}>{item.medicine_name}</td>
                      <td><code style={{ fontSize: 'var(--font-size-xs)' }}>{item.batch_number}</code></td>
                      <td>{item.quantity}</td>
                      <td><span className={getStatusBadgeClass(item.status)}>{statusLabel(item.status)}</span></td>
                      <td>{daysText(item.days_remaining)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h2>FEFO Queue</h2>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Next to Dispense</span>
          </div>
          {fefo_queue.length === 0 ? (
            <div className="empty-state" style={{ padding: 'var(--space-6)' }}>
              <Package size={32} />
              <h3>No Batches</h3>
              <p>No sellable batches in inventory</p>
            </div>
          ) : (
            <div className="fefo-queue">
              {fefo_queue.map((item, idx) => (
                <div key={item.batch_id}>
                  <div className="fefo-item clickable-row" onClick={() => navigate(`/medicines/${item.medicine_id}`)}>
                    <div className={`fefo-priority ${item.status === 'CRITICAL' ? 'critical' : item.status === 'EXPIRING_SOON' ? 'warning' : ''}`}>
                      #{item.fefo_priority}
                    </div>
                    <div className="fefo-item-details">
                      <div className="fefo-item-name">{item.batch_number}</div>
                      <div className="fefo-item-meta">
                        {item.medicine_name} · Expires {formatDate(item.expiry_date)} · {daysText(item.days_until_expiry)}
                      </div>
                    </div>
                    <div className="fefo-item-qty">{item.quantity} units</div>
                  </div>
                  {idx < fefo_queue.length - 1 && (
                    <div className="fefo-arrow"><ArrowDown size={14} /></div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Dispenses */}
      <div className="card">
        <div className="card-header">
          <h2>Recent Dispensing</h2>
          <button className="btn btn-outline btn-sm" onClick={() => navigate('/transactions')}>View All</button>
        </div>
        {recent_dispenses.length === 0 ? (
          <div className="empty-state" style={{ padding: 'var(--space-6)' }}>
            <ClipboardList size={32} />
            <h3>No Transactions</h3>
            <p>No dispensing transactions yet</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Medicine</th>
                  <th>Quantity</th>
                  <th>Batches</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {recent_dispenses.map((d) => (
                  <tr key={d.transaction_id} className="clickable-row" onClick={() => navigate('/transactions')}>
                    <td>#{d.transaction_id}</td>
                    <td style={{ fontWeight: 500 }}>{d.medicine_name}</td>
                    <td>{d.quantity}</td>
                    <td>{d.batch_count} batch{d.batch_count !== 1 ? 'es' : ''}</td>
                    <td><span className={getStatusBadgeClass(d.status)}>{d.status}</span></td>
                    <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>{d.created_at ? new Date(d.created_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
