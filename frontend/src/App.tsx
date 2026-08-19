import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { ReportsListPage } from './pages/ReportsListPage';
import { AppShell } from './layouts/AppShell';
import { ReportDashboardPage } from './pages/ReportDashboardPage';
import { EntitiesPage } from './pages/EntitiesPage';
import { EvidencePage } from './pages/EvidencePage';
import { FindingsPage } from './pages/FindingsPage';
import { RelationshipsPage } from './pages/RelationshipsPage';
import { TimelinePage } from './pages/TimelinePage';
import { GraphPage } from './pages/GraphPage';
import { InvestigatorChatPage } from './pages/InvestigatorChatPage';
import { QueryPage } from './pages/QueryPage';
import { PrivacyAuditPage } from './pages/PrivacyAuditPage';
import { HealthCheckPage } from './pages/HealthCheckPage';

const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Reports List Landing */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <ReportsListPage />
              </ProtectedRoute>
            }
          />

          {/* Protected Report-Scoped AppShell Routes */}
          <Route
            path="/reports/:reportId"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<ReportDashboardPage />} />
            <Route path="entities" element={<EntitiesPage />} />
            <Route path="evidence" element={<EvidencePage />} />
            <Route path="findings" element={<FindingsPage />} />
            <Route path="relationships" element={<RelationshipsPage />} />
            <Route path="timeline" element={<TimelinePage />} />
            <Route path="graph" element={<GraphPage />} />
            <Route path="chat" element={<InvestigatorChatPage />} />
            <Route path="query" element={<QueryPage />} />
            <Route path="privacy" element={<PrivacyAuditPage />} />
            <Route path="health" element={<HealthCheckPage />} />
          </Route>

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
