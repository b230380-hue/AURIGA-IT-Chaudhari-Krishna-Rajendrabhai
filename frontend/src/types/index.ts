/* PharmaFlow — Type definitions */

export interface Medicine {
  id: number;
  name: string;
  generic_name: string | null;
  manufacturer: string | null;
  strength: string | null;
  dosage_form: string | null;
  sku: string | null;
  created_at: string;
  updated_at: string;
}

export interface MedicineCreate {
  name: string;
  generic_name?: string;
  manufacturer?: string;
  strength?: string;
  dosage_form?: string;
  sku?: string;
}

export interface Batch {
  id: number;
  medicine_id: number;
  batch_number: string;
  quantity: number;
  initial_quantity: number;
  expiry_date: string;
  received_date: string | null;
  purchase_price: number | null;
  selling_price: number | null;
  created_at: string;
  updated_at: string;
  status: string | null;
  days_until_expiry: number | null;
  fefo_priority: number | null;
}

export interface BatchCreate {
  batch_number: string;
  quantity: number;
  expiry_date: string;
  received_date?: string;
  purchase_price?: number;
  selling_price?: number;
}

export interface MedicineStock {
  medicine_id: number;
  medicine_name: string;
  strength: string | null;
  dosage_form: string | null;
  physical_stock: number;
  sellable_stock: number;
  expired_stock: number;
  expiring_soon_stock: number;
  total_batches: number;
  valid_batches: number;
  expired_batches: number;
  next_expiry_date: string | null;
  next_expiry_days: number | null;
}

export interface MedicineSearchResult {
  id: number;
  name: string;
  generic_name: string | null;
  strength: string | null;
  dosage_form: string | null;
  manufacturer: string | null;
  sellable_stock: number;
  valid_batches: number;
  expired_batches: number;
  next_expiry_date: string | null;
  next_expiry_days: number | null;
  availability_status: 'IN_STOCK' | 'LOW_STOCK' | 'NO_SELLABLE_STOCK';
}

export interface AllocationDetail {
  batch_id: number;
  batch_number: string;
  expiry_date: string;
  quantity_dispensed: number;
  batch_remaining_after: number | null;
}

export interface DispensePreview {
  medicine_id: number;
  medicine_name: string;
  requested_quantity: number;
  feasible: boolean;
  available_stock: number;
  allocation_strategy: string;
  allocations: AllocationDetail[];
  remaining_sellable_after: number | null;
  why_first_batch: string | null;
}

export interface DispenseResult {
  transaction_id: number;
  medicine_id: number;
  medicine_name: string;
  requested_quantity: number;
  dispensed_quantity: number;
  allocation_strategy: string;
  allocations: AllocationDetail[];
  remaining_sellable_stock: number;
  status: string;
  created_at: string;
}

export interface DispenseTransaction {
  id: number;
  medicine_id: number;
  medicine_name: string | null;
  requested_quantity: number;
  dispensed_quantity: number;
  status: string;
  created_at: string;
  allocations: AllocationDetail[];
}

export interface ExpiryAlertItem {
  batch_id: number;
  medicine_id: number;
  medicine_name: string;
  batch_number: string;
  quantity: number;
  expiry_date: string;
  days_remaining: number;
  status: string;
  potential_value_at_risk: number | null;
}

export interface ExpiryAlertResponse {
  threshold_days: number;
  alerts: ExpiryAlertItem[];
  summary: Record<string, number>;
}

export interface DashboardSummary {
  total_medicines: number;
  total_batches: number;
  sellable_units: number;
  expired_units: number;
  expiring_soon_units: number;
  medicines_in_stock: number;
  batches_requiring_attention: number;
}

export interface InventoryHealth {
  score: number;
  grade: string;
  sellable_units: number;
  expired_units: number;
  expiring_soon_units: number;
  total_physical_units: number;
  sellable_percentage: number;
  expired_percentage: number;
  explanation: string;
}

export interface ExpiryExposure {
  units_expiring_within_30_days: number;
  units_expiring_within_7_days: number;
  potential_value_at_risk_30d: number | null;
  potential_value_at_risk_7d: number | null;
}

export interface FefoQueueItem {
  batch_id: number;
  medicine_id: number;
  medicine_name: string;
  batch_number: string;
  quantity: number;
  expiry_date: string;
  days_until_expiry: number;
  status: string;
  fefo_priority: number;
}

export interface RecentDispense {
  transaction_id: number;
  medicine_name: string;
  quantity: number;
  batch_count: number;
  created_at: string;
  status: string;
}

export interface DashboardData {
  summary: DashboardSummary;
  health: InventoryHealth;
  exposure: ExpiryExposure;
  needs_attention: ExpiryAlertItem[];
  fefo_queue: FefoQueueItem[];
  recent_dispenses: RecentDispense[];
}
