import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchReports, createSyntheticReport, ReportItem } from '../api/extraction';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';

export const ReportsListPage: React.FC = () => {
  const navigate = useNavigate();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState('');

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchReports();
      setReports(data);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadReports(); }, [loadReports]);

  const handleUpload = async () => {
    if (!filename.trim()) return;
    setUploading(true);
    try {
      const report = await createSyntheticReport(filename.trim(), [
        { page_number: 1, text_content: 'Synthetic UFDR report content for demonstration purposes.' },
      ]);
      setFilename('');
      await loadReports();
      navigate(`/reports/${report.id}/dashboard`);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="reports-list-page">
      <header className="topbar topbar-landing">
        <div className="topbar-brand">
          🛡️ UFDR Analysis Platform — <span className="topbar-sub">MHA Smart Automation</span>
        </div>
      </header>

      <div className="reports-list-content">
        <div className="rl-header">
          <h1>UFDR Forensic Reports</h1>
          <p className="text-secondary">Select an ingested report to begin analysis, or upload a new UFDR extraction.</p>
        </div>

        {/* Upload Card */}
        <div className="card upload-card">
          <h3>Upload New Report</h3>
          <div className="upload-row">
            <input
              type="text"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              placeholder="Enter UFDR report filename (e.g. Case_2024_08.xml)…"
              className="upload-input"
              onKeyDown={(e) => { if (e.key === 'Enter') handleUpload(); }}
            />
            <button className="btn-primary" onClick={handleUpload} disabled={uploading || !filename.trim()}>
              {uploading ? 'Uploading…' : 'Upload Report'}
            </button>
          </div>
        </div>

        {/* Reports Table */}
        {loading ? (
          <LoadingSpinner message="Loading reports…" />
        ) : reports.length === 0 ? (
          <EmptyState
            icon="📂"
            title="No reports uploaded yet"
            description="Upload a UFDR extraction file above to begin forensic analysis."
          />
        ) : (
          <div className="card">
            <div className="table-header-row">
              <h3>Ingested Reports</h3>
              <span className="text-small text-muted">{reports.length} report(s)</span>
            </div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Report ID</th>
                    <th>Filename</th>
                    <th>Pages</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id} className="clickable-row" onClick={() => navigate(`/reports/${r.id}/dashboard`)}>
                      <td className="font-mono text-small">{r.id}</td>
                      <td>{r.filename}</td>
                      <td>{r.page_count}</td>
                      <td><span className={`status-pill status-${r.status}`}>{r.status}</span></td>
                      <td className="text-small text-muted">{r.created_at?.slice(0, 19).replace('T', ' ')}</td>
                      <td><button className="btn-sm btn-primary">Open →</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
