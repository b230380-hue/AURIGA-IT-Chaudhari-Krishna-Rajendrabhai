import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getMedicine, getMedicineStock, getBatches, createBatch } from '../api/client';
import type { Medicine, MedicineStock, Batch } from '../types';
import { formatDate, daysText, getStatusBadgeClass, statusLabel } from '../utils/helpers';
import { ArrowLeft, Plus, X, ArrowRightLeft } from 'lucide-react';

export default function MedicineDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [medicine, setMedicine] = useState<Medicine | null>(null);
  const [stock, setStock] = useState<MedicineStock | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddBatch, setShowAddBatch] = useState(false);
  const [error, setError] = useState('');

  const medId = Number(id);

  const load = async () => {
    setLoading(true);
    try {
      const [med, st, bt] = await Promise.all([
        getMedicine(medId),
        getMedicineStock(medId),
        getBatches(medId),
      ]);
      setMedicine(med);
      setStock(st);
      setBatches(bt);
    } catch {
      setError('Failed to load medicine details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [medId]);

  if (loading) return <div className="loading"><div className="spinner" /> Loading…</div>;
  if (error) return <div className="error-message"><strong>Error</strong>{error}</div>;
  if (!medicine || !stock) return null;

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <button className="btn btn-outline btn-sm" onClick={() => navigate('/medicines')} style={{ marginBottom: 'var(--space-4)' }}>
          <ArrowLeft size={14} /> Back to Medicines
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700 }}>{medicine.name}</h1>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
              {[medicine.strength, medicine.dosage_form].filter(Boolean).join(' · ')}
              {medicine.manufacturer && ` — ${medicine.manufacturer}`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <button className="btn btn-primary" onClick={() => navigate(`/dispense?medicine=${medId}`)}>
              <ArrowRightLeft size={16} /> Dispense
            </button>
            <button className="btn btn-outline" onClick={() => setShowAddBatch(true)}>
              <Plus size={16} /> Add Batch
            </button>
          </div>
        </div>
      </div>

      {/* Stock Summary */}
      <div className="summary-grid" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="summary-card success">
          <div className="label">Sellable Stock</div>
          <div className="value">{stock.sellable_stock}</div>
        </div>
        <div className="summary-card">
          <div className="label">Physical Stock</div>
          <div className="value">{stock.physical_stock}</div>
        </div>
        <div className="summary-card danger">
          <div className="label">Expired Stock</div>
          <div className="value">{stock.expired_stock}</div>
        </div>
        <div className="summary-card warning">
          <div className="label">Expiring Soon</div>
          <div className="value">{stock.expiring_soon_stock}</div>
        </div>
        <div className="summary-card">
          <div className="label">Next Expiry</div>
          <div className="value" style={{ fontSize: 'var(--font-size-lg)' }}>
            {stock.next_expiry_days !== null ? daysText(stock.next_expiry_days) : '—'}
          </div>
        </div>
      </div>

      {stock.expired_stock > 0 && (
        <div className="error-message" style={{ marginBottom: 'var(--space-6)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <strong>{stock.expired_stock} expired units</strong> excluded from sellable stock
        </div>
      )}

      {/* Batch Table */}
      <div className="card">
        <div className="card-header">
          <h2>Batches ({batches.length})</h2>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>FEFO #</th>
                <th>Batch</th>
                <th>Quantity</th>
                <th>Initial</th>
                <th>Expiry Date</th>
                <th>Days Left</th>
                <th>Status</th>
                <th>Received</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => (
                <tr key={batch.id} style={batch.status === 'EXPIRED' ? { opacity: 0.6 } : {}}>
                  <td>
                    {batch.fefo_priority ? (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        width: 24, height: 24, borderRadius: '50%',
                        background: batch.status === 'CRITICAL' ? 'var(--color-danger)' : batch.status === 'EXPIRING_SOON' ? 'var(--color-warning)' : 'var(--color-primary)',
                        color: '#fff', fontSize: 'var(--font-size-xs)', fontWeight: 700,
                      }}>
                        {batch.fefo_priority}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--color-text-muted)' }}>—</span>
                    )}
                  </td>
                  <td><code style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>{batch.batch_number}</code></td>
                  <td style={{ fontWeight: 600 }}>{batch.quantity}</td>
                  <td style={{ color: 'var(--color-text-muted)' }}>{batch.initial_quantity}</td>
                  <td>{formatDate(batch.expiry_date)}</td>
                  <td>{daysText(batch.days_until_expiry)}</td>
                  <td>
                    <span className={getStatusBadgeClass(batch.status || '')}>{statusLabel(batch.status || '')}</span>
                  </td>
                  <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {batch.received_date ? formatDate(batch.received_date) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Batch Modal */}
      {showAddBatch && (
        <AddBatchModal
          medicineId={medId}
          medicineName={medicine.name}
          onClose={() => setShowAddBatch(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}

function AddBatchModal({ medicineId, medicineName, onClose, onCreated }: {
  medicineId: number; medicineName: string; onClose: () => void; onCreated: () => void;
}) {
  const [form, setForm] = useState({
    batch_number: '', quantity: '', expiry_date: '', received_date: '',
    purchase_price: '', selling_price: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.batch_number.trim() || !form.quantity || !form.expiry_date) {
      setError('Batch number, quantity, and expiry date are required');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await createBatch(medicineId, {
        batch_number: form.batch_number.trim(),
        quantity: parseInt(form.quantity),
        expiry_date: form.expiry_date,
        received_date: form.received_date || undefined,
        purchase_price: form.purchase_price ? parseFloat(form.purchase_price) : undefined,
        selling_price: form.selling_price ? parseFloat(form.selling_price) : undefined,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(detail?.message || 'Failed to add batch');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Add Batch — {medicineName}</h2>
          <button className="btn btn-outline btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        {error && <div className="error-message" style={{ marginBottom: 'var(--space-4)' }}>{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="batch-num">Batch Number *</label>
              <input id="batch-num" className="form-input" value={form.batch_number}
                onChange={(e) => setForm({ ...form, batch_number: e.target.value })} required />
            </div>
            <div className="form-group">
              <label htmlFor="batch-qty">Quantity *</label>
              <input id="batch-qty" type="number" min="0" className="form-input" value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })} required />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="batch-exp">Expiry Date *</label>
              <input id="batch-exp" type="date" className="form-input" value={form.expiry_date}
                onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} required />
            </div>
            <div className="form-group">
              <label htmlFor="batch-recv">Received Date</label>
              <input id="batch-recv" type="date" className="form-input" value={form.received_date}
                onChange={(e) => setForm({ ...form, received_date: e.target.value })} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="batch-pprice">Purchase Price</label>
              <input id="batch-pprice" type="number" step="0.01" min="0" className="form-input" value={form.purchase_price}
                onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} />
            </div>
            <div className="form-group">
              <label htmlFor="batch-sprice">Selling Price</label>
              <input id="batch-sprice" type="number" step="0.01" min="0" className="form-input" value={form.selling_price}
                onChange={(e) => setForm({ ...form, selling_price: e.target.value })} />
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Adding…' : 'Add Batch'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
