import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { OverviewPage } from './pages/OverviewPage';
import { FindingsPage } from './pages/FindingsPage';
import { FindingDetailPage } from './pages/FindingDetailPage';
import { GraphPage } from './pages/GraphPage';
import { InvestigationsPage } from './pages/InvestigationsPage';
import { ScansPage } from './pages/ScansPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="findings" element={<FindingsPage />} />
          <Route path="findings/:id" element={<FindingDetailPage />} />
          <Route path="graph" element={<GraphPage />} />
          <Route path="investigations" element={<InvestigationsPage />} />
          <Route path="scans" element={<ScansPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
