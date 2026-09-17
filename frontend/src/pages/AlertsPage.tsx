import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getExpiryAlerts } from '../api/client';
import type { ExpiryAlertResponse } from '../types';
import { formatDate, daysText, getStatusBadgeClass, statusLabel } from '../utils/helpers';
import { AlertTriangle, CheckCircle } from 'lucide-react';

const THRESHOLD_OPTIONS = [7, 30, 60, 90];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<ExpiryAlertResponse | null>(null);
  const [threshold, setThreshold] = useState(30);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    getExpiryAlerts(threshold)
      .then(setAlerts)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [threshold]);

  return (
    <div>
      <div className="page-header">
        <h1>Expiry Alerts</h1>
        <p>Batches that are expired or approaching expiry</p>
      </div>

      {/* Threshold tabs */}
      <div className="tabs">
        {THRESHOLD_OPTIONS.map((d) => (
          <button
            key={d}
            className={`tab ${threshold === d ? 'active' : ''}`}
            onClick={() => setThreshold(d)}
          >
            {d} Days
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /> Loading alerts…</div>
      ) : !alerts ? null : alerts.alerts.length === 0 ? (
        <div className="empty-state">
          <CheckCircle size={48} />
          <h3>No Alerts</h3>
          <p>No batches expiring within {threshold} days</p>
        </div>
      ) : (
        <>
          {/* Summary badges */}
          <div style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
            {alerts.summary.EXPIRED > 0 && (
              <div className="badge badge-expired" style={{ fontSize: 'var(--font-size-sm)', padding: '4px 12px' }}>
                {alerts.summary.EXPIRED} Expired
              </div>
            )}
            {alerts.summary.CRITICAL > 0 && (
              <div className="badge badge-critical" style={{ fontSize: 'var(--font-size-sm)', padding: '4px 12px' }}>
                {alerts.summary.CRITICAL} Critical
              </div>
            )}
            {alerts.summary.EXPIRING_SOON > 0 && (
              <div className="badge badge-expiring-soon" style={{ fontSize: 'var(--font-size-sm)', padding: '4px 12px' }}>
                {alerts.summary.EXPIRING_SOON} Expiring Soon
              </div>
            )}
          </div>

          <div className="card">
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Medicine</th>
                    <th>Batch</th>
                    <th>Quantity</th>
                    <th>Expiry Date</th>
                    <th>Days Left</th>
                    <th>Status</th>
                    <th>Value at Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.alerts.map((item) => (
                    <tr
                      key={item.batch_id}
                      className="clickable-row"
                      onClick={() => navigate(`/medicines/${item.medicine_id}`)}
                      style={item.status === 'EXPIRED' ? { opacity: 0.7 } : {}}
                    >
                      <td style={{ fontWeight: 500 }}>{item.medicine_name}</td>
                      <td><code style={{ fontSize: 'var(--font-size-xs)' }}>{item.batch_number}</code></td>
                      <td>{item.quantity}</td>
                      <td>{formatDate(item.expiry_date)}</td>
                      <td>{daysText(item.days_remaining)}</td>
                      <td><span className={getStatusBadgeClass(item.status)}>{statusLabel(item.status)}</span></td>
                      <td style={{ color: 'var(--color-text-muted)' }}>
                        {item.potential_value_at_risk !== null ? `$${item.potential_value_at_risk.toFixed(2)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
