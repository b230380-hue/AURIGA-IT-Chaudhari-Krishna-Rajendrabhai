import { useEffect, useState } from 'react';
import { getDispenses } from '../api/client';
import type { DispenseTransaction } from '../types';
import { formatDate, formatDateTime, getStatusBadgeClass } from '../utils/helpers';
import { ClipboardList, ChevronDown, ChevronUp, ArrowDown } from 'lucide-react';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<DispenseTransaction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    getDispenses(100)
      .then((data) => {
        setTransactions(data.transactions);
        setTotal(data.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /> Loading transactions…</div>;

  return (
    <div>
      <div className="page-header">
        <h1>Dispensing History</h1>
        <p>{total} total transaction{total !== 1 ? 's' : ''}</p>
      </div>

      {transactions.length === 0 ? (
        <div className="empty-state">
          <ClipboardList size={48} />
          <h3>No Transactions Yet</h3>
          <p>Dispensing transactions will appear here after medicines are dispensed</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Medicine</th>
                  <th>Requested</th>
                  <th>Dispensed</th>
                  <th>Batches</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => (
                  <>
                    <tr
                      key={txn.id}
                      className="clickable-row"
                      onClick={() => setExpanded(expanded === txn.id ? null : txn.id)}
                    >
                      <td style={{ fontWeight: 600 }}>#{txn.id}</td>
                      <td style={{ fontWeight: 500 }}>{txn.medicine_name || '—'}</td>
                      <td>{txn.requested_quantity}</td>
                      <td style={{ fontWeight: 600 }}>{txn.dispensed_quantity}</td>
                      <td>{txn.allocations.length}</td>
                      <td><span className={getStatusBadgeClass(txn.status)}>{txn.status}</span></td>
                      <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
                        {formatDateTime(txn.created_at)}
                      </td>
                      <td>
                        {expanded === txn.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </td>
                    </tr>
                    {expanded === txn.id && txn.allocations.length > 0 && (
                      <tr key={`${txn.id}-detail`}>
                        <td colSpan={8} style={{ padding: 'var(--space-4)', background: 'var(--color-surface-hover)' }}>
                          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)' }}>
                            FEFO Allocation Detail
                          </div>
                          <div className="allocation-flow">
                            {txn.allocations.map((alloc, idx) => (
                              <div key={alloc.batch_id}>
                                <div className="allocation-step" style={{ padding: 'var(--space-3)' }}>
                                  <div className="step-qty" style={{ fontSize: 'var(--font-size-lg)' }}>{alloc.quantity_dispensed}</div>
                                  <div className="step-info">
                                    <div className="step-batch">{alloc.batch_number}</div>
                                    <div className="step-expiry">Expiry: {formatDate(alloc.expiry_date)}</div>
                                  </div>
                                </div>
                                {idx < txn.allocations.length - 1 && (
                                  <div className="allocation-connector"><ArrowDown size={14} /></div>
                                )}
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
