import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { searchMedicines, getMedicineStock, previewDispense, executeDispense } from '../api/client';
import type { MedicineSearchResult, MedicineStock, DispensePreview, DispenseResult } from '../types';
import { formatDate, daysText, getStatusBadgeClass, statusLabel } from '../utils/helpers';
import { Search, ArrowDown, CheckCircle, AlertTriangle, Info } from 'lucide-react';

type Step = 'search' | 'preview' | 'receipt';

export default function DispensePage() {
  const [searchParams] = useSearchParams();
  const initialMedId = searchParams.get('medicine');

  const [step, setStep] = useState<Step>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<MedicineSearchResult[]>([]);
  const [selectedMedicine, setSelectedMedicine] = useState<MedicineSearchResult | null>(null);
  const [stock, setStock] = useState<MedicineStock | null>(null);
  const [quantity, setQuantity] = useState('');
  const [preview, setPreview] = useState<DispensePreview | null>(null);
  const [receipt, setReceipt] = useState<DispenseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // If medicine ID passed via URL, auto-select it
  useEffect(() => {
    if (initialMedId) {
      searchMedicines(initialMedId).then((results) => {
        const match = results.find((r) => r.id === Number(initialMedId));
        if (match) selectMedicine(match);
      }).catch(() => {});
    }
  }, [initialMedId]);

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (q.length < 1) { setSearchResults([]); return; }
    try {
      const results = await searchMedicines(q);
      setSearchResults(results);
    } catch { /* ignore */ }
  };

  const selectMedicine = async (med: MedicineSearchResult) => {
    setSelectedMedicine(med);
    setSearchResults([]);
    setSearchQuery(med.name);
    try {
      const st = await getMedicineStock(med.id);
      setStock(st);
    } catch { /* ignore */ }
  };

  const handlePreview = async () => {
    if (!selectedMedicine || !quantity) return;
    const qty = parseInt(quantity);
    if (qty <= 0 || isNaN(qty)) { setError('Please enter a valid positive quantity'); return; }
    setLoading(true);
    setError('');
    try {
      const p = await previewDispense(selectedMedicine.id, qty);
      setPreview(p);
      setStep('preview');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(detail?.message || 'Failed to preview dispense');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!selectedMedicine || !quantity) return;
    setLoading(true);
    setError('');
    try {
      const result = await executeDispense(selectedMedicine.id, parseInt(quantity));
      setReceipt(result);
      setStep('receipt');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(detail?.message || 'Failed to dispense');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setStep('search');
    setSelectedMedicine(null);
    setStock(null);
    setQuantity('');
    setPreview(null);
    setReceipt(null);
    setSearchQuery('');
    setError('');
  };

  return (
    <div className="dispense-workflow">
      <div className="page-header">
        <h1>Dispense Medicine</h1>
        <p>FEFO-protected dispensing workflow</p>
      </div>

      {error && (
        <div className="error-message" style={{ marginBottom: 'var(--space-4)' }}>
          <strong><AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />Dispensing Error</strong>
          {error}
        </div>
      )}

      {/* Step 1: Search & Select */}
      {step === 'search' && (
        <div>
          <div className="dispense-step">
            <div className="step-label"><span className="step-number">1</span> Select Medicine</div>
            <div className="search-container" style={{ marginBottom: 'var(--space-2)' }}>
              <Search />
              <input
                type="text"
                className="search-input"
                placeholder="Search medicine name…"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                aria-label="Search medicine to dispense"
              />
            </div>

            {/* Search results dropdown */}
            {searchResults.length > 0 && !selectedMedicine && (
              <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
                {searchResults.map((r) => (
                  <div
                    key={r.id}
                    className="clickable-row"
                    style={{ padding: 'var(--space-3) var(--space-4)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border)' }}
                    onClick={() => selectMedicine(r)}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{r.name} {r.strength}</div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                        {r.dosage_form} · {r.sellable_stock} sellable
                      </div>
                    </div>
                    <span className={getStatusBadgeClass(r.availability_status)}>
                      {r.availability_status === 'IN_STOCK' ? 'In Stock' : r.availability_status === 'LOW_STOCK' ? 'Low Stock' : 'No Stock'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Selected medicine info */}
          {selectedMedicine && stock && (
            <>
              <div className="dispense-step">
                <div className="step-label"><span className="step-number">2</span> Stock Information</div>
                <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)' }}>{selectedMedicine.name} {selectedMedicine.strength}</div>
                      <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>{selectedMedicine.dosage_form}</div>
                    </div>
                    <button className="btn btn-outline btn-sm" onClick={handleReset}>Change</button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-4)' }}>
                    <div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Sellable Stock</div>
                      <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--color-success)' }}>{stock.sellable_stock}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Valid Batches</div>
                      <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>{stock.valid_batches}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Nearest Expiry</div>
                      <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: stock.next_expiry_days !== null && stock.next_expiry_days <= 7 ? 'var(--color-danger)' : 'var(--color-text)' }}>
                        {stock.next_expiry_days !== null ? daysText(stock.next_expiry_days) : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="dispense-step">
                <div className="step-label"><span className="step-number">3</span> Enter Quantity</div>
                <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-end' }}>
                  <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                    <label htmlFor="disp-qty">Units to dispense</label>
                    <input
                      id="disp-qty"
                      type="number"
                      min="1"
                      max={stock.sellable_stock}
                      className="form-input"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      placeholder={`Max ${stock.sellable_stock}`}
                    />
                  </div>
                  <button
                    className="btn btn-primary btn-lg"
                    onClick={handlePreview}
                    disabled={loading || !quantity || parseInt(quantity) <= 0}
                    style={{ marginBottom: 0, height: 42 }}
                  >
                    {loading ? 'Loading…' : 'Preview FEFO Allocation'}
                  </button>
                </div>
                {parseInt(quantity) > stock.sellable_stock && (
                  <div className="error-message" style={{ marginTop: 'var(--space-3)' }}>
                    Cannot dispense {quantity} units. Only {stock.sellable_stock} non-expired units available.
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Step 4: Preview */}
      {step === 'preview' && preview && (
        <div>
          <div className="dispense-step">
            <div className="step-label"><span className="step-number">4</span> FEFO Allocation Preview</div>

            {!preview.feasible ? (
              <div className="error-message">
                <strong>Insufficient Stock</strong>
                Cannot dispense {preview.requested_quantity} units. Only {preview.available_stock} non-expired units available.
              </div>
            ) : (
              <>
                <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-4)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                    <Info size={14} />
                    This preview shows how {preview.requested_quantity} units will be allocated across batches using {preview.allocation_strategy}.
                    No inventory has been modified.
                  </div>

                  <div className="allocation-flow">
                    {preview.allocations.map((alloc, idx) => (
                      <div key={alloc.batch_id}>
                        <div className="allocation-step">
                          <div className="step-qty">{alloc.quantity_dispensed}</div>
                          <div className="step-info">
                            <div className="step-batch">{alloc.batch_number}</div>
                            <div className="step-expiry">Expires {formatDate(alloc.expiry_date)} · {alloc.batch_remaining_after} units remaining after</div>
                          </div>
                        </div>
                        {idx < preview.allocations.length - 1 && (
                          <div className="allocation-connector"><ArrowDown size={16} /></div>
                        )}
                      </div>
                    ))}
                  </div>

                  {preview.remaining_sellable_after !== null && (
                    <div style={{ marginTop: 'var(--space-4)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                      Remaining sellable stock after dispense: <strong>{preview.remaining_sellable_after}</strong>
                    </div>
                  )}
                </div>

                {/* Why this batch? */}
                {preview.why_first_batch && (
                  <div className="why-first-batch" style={{ marginBottom: 'var(--space-4)' }}>
                    <strong style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Why this batch?</strong>
                    <div style={{ marginTop: 4 }}>{preview.why_first_batch}</div>
                  </div>
                )}

                <div className="dispense-step">
                  <div className="step-label"><span className="step-number">5</span> Confirm Dispense</div>
                  <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
                    <button className="btn btn-outline" onClick={() => { setStep('search'); setPreview(null); setError(''); }}>
                      ← Back
                    </button>
                    <button className="btn btn-success btn-lg" onClick={handleConfirm} disabled={loading}>
                      {loading ? 'Dispensing…' : `Confirm Dispense ${preview.requested_quantity} Units`}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Step 6: Receipt */}
      {step === 'receipt' && receipt && (
        <div>
          <div className="dispense-receipt">
            <div className="receipt-header">
              <CheckCircle size={28} />
              <h3>{receipt.dispensed_quantity} units dispensed successfully across {receipt.allocations.length} batch{receipt.allocations.length !== 1 ? 'es' : ''}</h3>
            </div>

            <div className="receipt-summary">
              <div className="receipt-stat">
                <div className="stat-label">Transaction</div>
                <div className="stat-value">#{receipt.transaction_id}</div>
              </div>
              <div className="receipt-stat">
                <div className="stat-label">Dispensed</div>
                <div className="stat-value">{receipt.dispensed_quantity}</div>
              </div>
              <div className="receipt-stat">
                <div className="stat-label">Remaining</div>
                <div className="stat-value">{receipt.remaining_sellable_stock}</div>
              </div>
            </div>

            <div className="allocation-flow">
              {receipt.allocations.map((alloc, idx) => (
                <div key={alloc.batch_id}>
                  <div className="allocation-step">
                    <div className="step-qty">{alloc.quantity_dispensed}</div>
                    <div className="step-info">
                      <div className="step-batch">{alloc.batch_number}</div>
                      <div className="step-expiry">Expires {formatDate(alloc.expiry_date)}</div>
                    </div>
                  </div>
                  {idx < receipt.allocations.length - 1 && (
                    <div className="allocation-connector"><ArrowDown size={16} /></div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ marginTop: 'var(--space-6)', display: 'flex', gap: 'var(--space-3)' }}>
              <button className="btn btn-primary" onClick={handleReset}>Dispense Another</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
