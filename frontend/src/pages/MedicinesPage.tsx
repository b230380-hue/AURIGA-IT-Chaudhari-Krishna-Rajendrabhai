import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMedicines, searchMedicines, createMedicine, getMedicineStock } from '../api/client';
import type { Medicine, MedicineStock } from '../types';
import { Search, Plus, Pill, X } from 'lucide-react';
import { getStatusBadgeClass, daysText, availabilityLabel } from '../utils/helpers';

export default function MedicinesPage() {
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [stockMap, setStockMap] = useState<Record<number, MedicineStock>>({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const loadMedicines = async () => {
    setLoading(true);
    try {
      const meds = searchQuery
        ? (await searchMedicines(searchQuery)).map((r) => ({
            id: r.id,
            name: r.name,
            generic_name: r.generic_name,
            manufacturer: r.manufacturer,
            strength: r.strength,
            dosage_form: r.dosage_form,
            sku: null,
            created_at: '',
            updated_at: '',
          }))
        : await getMedicines();
      setMedicines(meds);

      // Load stock for each
      const stocks: Record<number, MedicineStock> = {};
      await Promise.all(
        meds.map(async (m) => {
          try {
            stocks[m.id] = await getMedicineStock(m.id);
          } catch { /* ignore */ }
        })
      );
      setStockMap(stocks);
    } catch {
      setError('Failed to load medicines');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(loadMedicines, searchQuery ? 300 : 0);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const getAvailability = (stock?: MedicineStock) => {
    if (!stock) return 'NO_SELLABLE_STOCK';
    if (stock.sellable_stock > 20) return 'IN_STOCK';
    if (stock.sellable_stock > 0) return 'LOW_STOCK';
    return 'NO_SELLABLE_STOCK';
  };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Medicines</h1>
          <p>Inventory catalog with sellable availability</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
          <Plus size={16} /> Add Medicine
        </button>
      </div>

      <div className="search-container">
        <Search />
        <input
          type="text"
          className="search-input"
          placeholder="Search medicines by name…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search medicines"
        />
      </div>

      {error && <div className="error-message"><strong>Error</strong>{error}</div>}

      {loading ? (
        <div className="loading"><div className="spinner" /> Loading medicines…</div>
      ) : medicines.length === 0 ? (
        <div className="empty-state">
          <Pill size={48} />
          <h3>No medicines found</h3>
          <p>{searchQuery ? `No results for "${searchQuery}"` : 'Add your first medicine to get started'}</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Medicine</th>
                  <th>Strength</th>
                  <th>Form</th>
                  <th>Sellable Stock</th>
                  <th>Batches</th>
                  <th>Next Expiry</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {medicines.map((med) => {
                  const stock = stockMap[med.id];
                  const avail = getAvailability(stock);
                  return (
                    <tr
                      key={med.id}
                      className="clickable-row"
                      onClick={() => navigate(`/medicines/${med.id}`)}
                    >
                      <td>
                        <div style={{ fontWeight: 600 }}>{med.name}</div>
                        {med.generic_name && (
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                            {med.generic_name}
                          </div>
                        )}
                      </td>
                      <td>{med.strength || '—'}</td>
                      <td>{med.dosage_form || '—'}</td>
                      <td style={{ fontWeight: 600 }}>{stock?.sellable_stock ?? 0}</td>
                      <td>{stock?.valid_batches ?? 0} valid{stock?.expired_batches ? `, ${stock.expired_batches} expired` : ''}</td>
                      <td>{stock?.next_expiry_days !== null && stock?.next_expiry_days !== undefined ? daysText(stock.next_expiry_days) : '—'}</td>
                      <td><span className={getStatusBadgeClass(avail)}>{availabilityLabel(avail)}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Medicine Modal */}
      {showAdd && <AddMedicineModal onClose={() => setShowAdd(false)} onCreated={loadMedicines} />}
    </div>
  );
}

function AddMedicineModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    name: '', generic_name: '', manufacturer: '', strength: '', dosage_form: '', sku: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) { setError('Name is required'); return; }
    setSubmitting(true);
    setError('');
    try {
      await createMedicine({
        name: form.name.trim(),
        generic_name: form.generic_name.trim() || undefined,
        manufacturer: form.manufacturer.trim() || undefined,
        strength: form.strength.trim() || undefined,
        dosage_form: form.dosage_form.trim() || undefined,
        sku: form.sku.trim() || undefined,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(detail?.message || detail?.error || 'Failed to create medicine');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Add Medicine</h2>
          <button className="btn btn-outline btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        {error && <div className="error-message" style={{ marginBottom: 'var(--space-4)' }}>{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="med-name">Name *</label>
            <input id="med-name" className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Paracetamol" required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="med-generic">Generic Name</label>
              <input id="med-generic" className="form-input" value={form.generic_name} onChange={(e) => setForm({ ...form, generic_name: e.target.value })} placeholder="e.g. Acetaminophen" />
            </div>
            <div className="form-group">
              <label htmlFor="med-mfr">Manufacturer</label>
              <input id="med-mfr" className="form-input" value={form.manufacturer} onChange={(e) => setForm({ ...form, manufacturer: e.target.value })} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="med-strength">Strength</label>
              <input id="med-strength" className="form-input" value={form.strength} onChange={(e) => setForm({ ...form, strength: e.target.value })} placeholder="e.g. 500mg" />
            </div>
            <div className="form-group">
              <label htmlFor="med-form">Dosage Form</label>
              <input id="med-form" className="form-input" value={form.dosage_form} onChange={(e) => setForm({ ...form, dosage_form: e.target.value })} placeholder="e.g. Tablet" />
            </div>
            <div className="form-group">
              <label htmlFor="med-sku">SKU</label>
              <input id="med-sku" className="form-input" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} placeholder="e.g. PARA-500" />
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create Medicine'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
