import { useState } from 'react';
import { importBatches } from '../api/client';
import type { ImportReport } from '../types';
import { Upload, CheckCircle2, Copy, AlertCircle, RefreshCw } from 'lucide-react';

const SAMPLE_MESSY_DATA = `[
  { "medicine_name": "Paracetamol", "batch_number": "PARA-IMP1", "quantity": "25 units", "expiry_date": "15/12/2026" },
  { "medicine_name": "Paracetamol", "batch_number": "PARA-IMP1", "quantity": "15 units", "expiry_date": "15/12/2026" },
  { "medicine_name": "Amoxicillin", "batch_number": "AMOX-IMP2", "quantity": " 50 boxes ", "expiry_date": "2027-04-10" },
  { "medicine_name": null, "batch_number": "ERR-NO-NAME", "quantity": "100", "expiry_date": "2026-11-20" },
  { "medicine_name": "Ibuprofen", "batch_number": "", "quantity": "30", "expiry_date": "2027-01-01" },
  { "medicine_name": "Cetirizine", "batch_number": "CET-BADQTY", "quantity": "not a number", "expiry_date": "2027-02-15" },
  { "medicine_name": "Cetirizine", "batch_number": "CET-VALID", "quantity": 40, "expiry_date": "28-02-2027" }
]`;

export default function ImportPage() {
  const [inputData, setInputData] = useState(SAMPLE_MESSY_DATA);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [error, setError] = useState('');

  const handleImport = async () => {
    setLoading(true);
    setError('');
    try {
      let parsedPayload: any;
      try {
        parsedPayload = JSON.parse(inputData);
      } catch {
        parsedPayload = inputData; // treat as CSV/text
      }

      const res = await importBatches(parsedPayload);
      setReport(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to import batches. Please check format.');
    } finally {
      setLoading(false);
    }
  };

  const loadSample = () => {
    setInputData(SAMPLE_MESSY_DATA);
    setReport(null);
    setError('');
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2>Messy Batch Import</h2>
          <p className="text-secondary">
            Level 2 — T4 (Messy Data): Handles nulls, unit strings ('10 units'), dd/mm/yyyy vs ISO dates, and duplicate rows.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={loadSample}>
          <RefreshCw size={16} />
          Load Sample Dataset
        </button>
      </div>

      <div className="grid-2col" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Input Panel */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <h3>Batch Data Input (JSON or CSV)</h3>
            <span className="badge badge-info">Auto-Clean & Dedup</span>
          </div>

          <textarea
            className="input"
            rows={16}
            style={{
              fontFamily: 'monospace',
              fontSize: '0.85rem',
              width: '100%',
              resize: 'vertical',
              padding: '0.75rem',
              borderRadius: '6px',
            }}
            value={inputData}
            onChange={(e) => setInputData(e.target.value)}
            placeholder="Paste JSON array or CSV here..."
          />

          <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button className="btn btn-primary" onClick={handleImport} disabled={loading || !inputData.trim()}>
              <Upload size={16} />
              {loading ? 'Processing...' : 'Run Import Pipeline'}
            </button>
          </div>

          {error && (
            <div className="alert alert-error" style={{ marginTop: '1rem' }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Results Panel */}
        <div className="card">
          <div className="card-header">
            <h3>Import & Deduplication Report</h3>
          </div>

          {report ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                <div className="stat-card" style={{ background: '#ecfdf5', border: '1px solid #a7f3d0' }}>
                  <div style={{ fontSize: '0.8rem', color: '#065f46', fontWeight: 600 }}>IMPORTED</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#047857' }}>{report.imported}</div>
                  <div style={{ fontSize: '0.75rem', color: '#047857' }}>New batches added</div>
                </div>

                <div className="stat-card" style={{ background: '#eff6ff', border: '1px solid #bfdbfe' }}>
                  <div style={{ fontSize: '0.8rem', color: '#1e40af', fontWeight: 600 }}>DEDUPED</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#1d4ed8' }}>{report.deduped}</div>
                  <div style={{ fontSize: '0.75rem', color: '#1d4ed8' }}>Merged / skipped duplicates</div>
                </div>

                <div className="stat-card" style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
                  <div style={{ fontSize: '0.8rem', color: '#991b1b', fontWeight: 600 }}>REJECTED</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#b91c1c' }}>{report.rejected}</div>
                  <div style={{ fontSize: '0.75rem', color: '#b91c1c' }}>Null / invalid rows</div>
                </div>
              </div>

              {report.errors && report.errors.length > 0 && (
                <div>
                  <h4 style={{ marginBottom: '0.5rem', color: '#991b1b', fontSize: '0.9rem' }}>
                    Rejected Rows Reason Log:
                  </h4>
                  <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                    <table className="table" style={{ fontSize: '0.85rem' }}>
                      <thead>
                        <tr>
                          <th>Row</th>
                          <th>Rejection Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.errors.map((err, i) => (
                          <tr key={i}>
                            <td><strong>Row {err.row}</strong></td>
                            <td style={{ color: '#b91c1c' }}>{err.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <Copy size={40} style={{ opacity: 0.3, marginBottom: '1rem' }} />
              <p>Click <strong>"Run Import Pipeline"</strong> to process the messy batch dataset.</p>
              <p style={{ fontSize: '0.85rem' }}>The pipeline will clean dirty quantities, normalize dates, and deduplicate.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
