import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import MedicinesPage from './pages/MedicinesPage';
import MedicineDetailPage from './pages/MedicineDetailPage';
import DispensePage from './pages/DispensePage';
import AlertsPage from './pages/AlertsPage';
import TransactionsPage from './pages/TransactionsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="medicines" element={<MedicinesPage />} />
          <Route path="medicines/:id" element={<MedicineDetailPage />} />
          <Route path="dispense" element={<DispensePage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
