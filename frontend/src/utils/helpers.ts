/* Utility helpers for the frontend */

export function getStatusBadgeClass(status: string): string {
  switch (status) {
    case 'EXPIRED':
      return 'badge badge-expired';
    case 'CRITICAL':
      return 'badge badge-critical';
    case 'EXPIRING_SOON':
      return 'badge badge-expiring-soon';
    case 'HEALTHY':
      return 'badge badge-healthy';
    case 'IN_STOCK':
      return 'badge badge-in-stock';
    case 'LOW_STOCK':
      return 'badge badge-low-stock';
    case 'NO_SELLABLE_STOCK':
      return 'badge badge-no-stock';
    case 'COMPLETED':
      return 'badge badge-completed';
    default:
      return 'badge';
  }
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr + (dateStr.includes('T') ? '' : 'T00:00:00'));
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatDateTime(dateStr: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function daysText(days: number | null | undefined): string {
  if (days === null || days === undefined) return '—';
  if (days < 0) return `${Math.abs(days)}d expired`;
  if (days === 0) return 'Today';
  if (days === 1) return '1 day';
  return `${days} days`;
}

export function availabilityLabel(status: string): string {
  switch (status) {
    case 'IN_STOCK':
      return 'In Stock';
    case 'LOW_STOCK':
      return 'Low Stock';
    case 'NO_SELLABLE_STOCK':
      return 'No Sellable Stock';
    default:
      return status;
  }
}

export function statusLabel(status: string): string {
  switch (status) {
    case 'EXPIRED':
      return 'Expired';
    case 'CRITICAL':
      return 'Critical';
    case 'EXPIRING_SOON':
      return 'Expiring Soon';
    case 'HEALTHY':
      return 'Healthy';
    default:
      return status;
  }
}
