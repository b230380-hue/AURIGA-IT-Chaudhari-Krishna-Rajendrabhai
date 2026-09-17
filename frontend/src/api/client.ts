/* PharmaFlow — API Client */

import axios from 'axios';
import type {
  Medicine,
  MedicineCreate,
  MedicineStock,
  MedicineSearchResult,
  Batch,
  BatchCreate,
  DispensePreview,
  DispenseResult,
  DispenseTransaction,
  ExpiryAlertResponse,
  DashboardData,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: { 'Content-Type': 'application/json' },
});

// ── Medicine ──────────────────────────────────────────────────

export const getMedicines = () =>
  api.get<Medicine[]>('/medicines').then((r) => r.data);

export const getMedicine = (id: number) =>
  api.get<Medicine>(`/medicines/${id}`).then((r) => r.data);

export const createMedicine = (data: MedicineCreate) =>
  api.post<Medicine>('/medicines', data).then((r) => r.data);

export const updateMedicine = (id: number, data: Partial<MedicineCreate>) =>
  api.put<Medicine>(`/medicines/${id}`, data).then((r) => r.data);

export const searchMedicines = (q: string) =>
  api.get<MedicineSearchResult[]>('/medicines/search', { params: { q } }).then((r) => r.data);

export const getMedicineStock = (id: number) =>
  api.get<MedicineStock>(`/medicines/${id}/stock`).then((r) => r.data);

// ── Batches ───────────────────────────────────────────────────

export const getBatches = (medicineId: number) =>
  api.get<Batch[]>(`/medicines/${medicineId}/batches`).then((r) => r.data);

export const createBatch = (medicineId: number, data: BatchCreate) =>
  api.post<Batch>(`/medicines/${medicineId}/batches`, data).then((r) => r.data);

// ── Dispensing ────────────────────────────────────────────────

export const previewDispense = (medicineId: number, quantity: number) =>
  api
    .post<DispensePreview>(`/medicines/${medicineId}/dispense/preview`, { quantity })
    .then((r) => r.data);

export const executeDispense = (medicineId: number, quantity: number) =>
  api
    .post<DispenseResult>(`/medicines/${medicineId}/dispense`, { quantity })
    .then((r) => r.data);

export const getDispenses = (limit = 50, offset = 0) =>
  api
    .get<{ transactions: DispenseTransaction[]; total: number }>('/dispenses', {
      params: { limit, offset },
    })
    .then((r) => r.data);

export const getDispense = (id: number) =>
  api.get<DispenseTransaction>(`/dispenses/${id}`).then((r) => r.data);

// ── Alerts ────────────────────────────────────────────────────

export const getExpiryAlerts = (days = 30) =>
  api.get<ExpiryAlertResponse>('/alerts/expiry', { params: { days } }).then((r) => r.data);

// ── Dashboard ─────────────────────────────────────────────────

export const getDashboard = () =>
  api.get<DashboardData>('/dashboard').then((r) => r.data);

export default api;
