import { useEffect, useState } from 'react';
import { getClock, postClock, resetClock, getOutbox, clearOutbox } from '../api/client';
import type { ClockReport, OutboxMessage } from '../types';
import { Clock, Bell, Play, RotateCcw, AlertTriangle, CheckCircle, Trash2 } from 'lucide-react';

export default function AutomationPage() {
  const [currentDate, setCurrentDate] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [advanceDays, setAdvanceDays] = useState(1);
  const [report, setReport] = useState<ClockReport | null>(null);
  const [outbox, setOutbox] = useState<OutboxMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState('');

  const refreshState = async () => {
    try {
      const clock = await getClock();
      setCurrentDate(clock.date);
      const msgs = await getOutbox();
      setOutbox(msgs);
    } catch {
      // Ignore network errors on uninitialized backend
    }
  };

  useEffect(() => {
    refreshState();
  }, []);

  const handleAdvanceDays = async (days: number) => {
    setLoading(true);
    setActionMsg('');
    try {
      const rep = await postClock({ days });
      setReport(rep);
      setCurrentDate(rep.date);
      setActionMsg(`Advanced ${days} day(s). Daily automation job executed.`);
      const msgs = await getOutbox();
      setOutbox(msgs);
    } catch (err: any) {
      setActionMsg('Failed to advance clock.');
    } finally {
      setLoading(false);
    }
  };

  const handleSetCustomDate = async () => {
    if (!targetDate) return;
    setLoading(true);
    setActionMsg('');
    try {
      const rep = await postClock({ date: targetDate });
      setReport(rep);
      setCurrentDate(rep.date);
      setActionMsg(`Clock set to ${targetDate}. Daily automation job executed.`);
      const msgs = await getOutbox();
      setOutbox(msgs);
    } catch (err: any) {
      setActionMsg('Failed to set clock date.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setActionMsg('');
    try {
      const rep = await resetClock();
      setReport(rep);
      setCurrentDate(rep.date);
      setActionMsg('Clock reset to real system date.');
      const msgs = await getOutbox();
      setOutbox(msgs);
    } catch {
      setActionMsg('Failed to reset clock.');
    } finally {
      setLoading(false);
    }
  };

  const handleClearOutbox = async () => {
    try {
      await clearOutbox();
      setOutbox([]);
    } catch {
      // ignore
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2>Daily Automation & Notification Outbox</h2>
          <p className="text-secondary">
            Level 1 (T2 automation via POST /clock) & Level 3 (T1 notification service via /outbox).
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="badge badge-info" style={{ fontSize: '0.9rem', padding: '0.4rem 0.75rem' }}>
            <Clock size={14} style={{ marginRight: '0.25rem' }} />
            Active Date: <strong>{currentDate || 'Loading...'}</strong>
          </span>
          <button className="btn btn-secondary" onClick={handleReset} disabled={loading}>
            <RotateCcw size={14} />
            Reset to Today
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="alert alert-info" style={{ marginBottom: '1.5rem' }}>
          <CheckCircle size={16} />
          <span>{actionMsg}</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Clock Controls */}
        <div className="card">
          <div className="card-header">
            <h3>Automated Daily Clock (POST /clock)</h3>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Advancing the clock runs the daily job: flags batches expiring within 7 days, quarantines expired ones, and triggers re-order alerts if in-date stock falls below threshold.
          </p>

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
            <button className="btn btn-primary" onClick={() => handleAdvanceDays(1)} disabled={loading}>
              <Play size={14} />
              Advance +1 Day
            </button>
            <button className="btn btn-secondary" onClick={() => handleAdvanceDays(7)} disabled={loading}>
              +7 Days
            </button>
            <button className="btn btn-secondary" onClick={() => handleAdvanceDays(30)} disabled={loading}>
              +30 Days
            </button>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="date"
              className="input"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              style={{ maxWidth: '200px' }}
            />
            <button className="btn btn-secondary" onClick={handleSetCustomDate} disabled={loading || !targetDate}>
              Jump to Date
            </button>
          </div>
        </div>

        {/* Daily Job Report */}
        <div className="card">
          <div className="card-header">
            <h3>Latest Daily Job Report</h3>
          </div>

          {report ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div className="stat-card" style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
                  <div style={{ fontSize: '0.8rem', color: '#991b1b', fontWeight: 600 }}>QUARANTINED</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#b91c1c' }}>{report.quarantined}</div>
                  <div style={{ fontSize: '0.75rem', color: '#b91c1c' }}>Batches expired & quarantined</div>
                </div>

                <div className="stat-card" style={{ background: '#fffbeb', border: '1px solid #fde68a' }}>
                  <div style={{ fontSize: '0.8rem', color: '#92400e', fontWeight: 600 }}>FLAGGED (7 DAYS)</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#b45309' }}>{report.flagged}</div>
                  <div style={{ fontSize: '0.75rem', color: '#b45309' }}>Expiring within 7 days</div>
                </div>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '4px' }}>
                {report.report}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-secondary)' }}>
              <Clock size={36} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p>Advance the clock or jump to a date to trigger the daily job.</p>
            </div>
          )}
        </div>
      </div>

      {/* Outbox Notifications Section */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bell size={18} />
            <h3>Notification Service Outbox (/outbox)</h3>
            <span className="badge badge-critical">{outbox.length} pending alerts</span>
          </div>
          {outbox.length > 0 && (
            <button className="btn btn-secondary" onClick={handleClearOutbox} style={{ color: '#b91c1c' }}>
              <Trash2 size={14} />
              Clear Outbox
            </button>
          )}
        </div>

        {outbox.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Medicine</th>
                  <th>Event</th>
                  <th>Current Sellable Stock</th>
                  <th>Reorder Threshold</th>
                  <th>Notification Message</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {outbox.map((msg) => (
                  <tr key={msg.id}>
                    <td><strong>{msg.medicine_name}</strong></td>
                    <td>
                      <span className="badge badge-critical">{msg.event}</span>
                    </td>
                    <td>
                      <span style={{ color: '#b91c1c', fontWeight: 600 }}>{msg.current_stock} units</span>
                    </td>
                    <td>{msg.threshold} units</td>
                    <td style={{ fontSize: '0.85rem' }}>{msg.message}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {new Date(msg.created_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-secondary)' }}>
            <CheckCircle size={36} style={{ color: '#059669', opacity: 0.5, marginBottom: '0.5rem' }} />
            <p>Outbox is clear. All medicines currently meet or exceed their in-date reorder thresholds.</p>
          </div>
        )}
      </div>
    </div>
  );
}
