import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchReports, uploadReportFile, createSyntheticReport, ReportItem } from '../api/extraction';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';

export const ReportsListPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await fetchReports();
      setReports(data);
    } catch (err: any) {
      console.error('Failed to load reports:', err);
      setErrorMessage('Failed to connect to backend server.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadReports(); }, [loadReports]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileUploadSubmit = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setErrorMessage(null);
    try {
      const report = await uploadReportFile(selectedFile);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadReports();
      navigate(`/reports/${report.id}/dashboard`);
    } catch (err: any) {
      console.error('Upload failed:', err);
      setErrorMessage(err?.response?.data?.detail || 'Failed to upload XML report.');
    } finally {
      setUploading(false);
    }
  };

  const handleSeedDemoCase = async () => {
    setUploading(true);
    setErrorMessage(null);
    try {
      const demoFilename = `UFDR_Case_Demo_${Date.now().toString().slice(-4)}.xml`;
      const report = await createSyntheticReport(demoFilename, [
        { page_number: 1, text_content: 'Suspect Vikram (+91 9876543210) visited Connaught Place and New Delhi. Contact vikram@forensics.gov.in.' },
        { page_number: 2, text_content: 'Associate Rahul Sharma (rahul@techcorp.in) accessed IP 192.168.1.100 on 12 March 2024.' },
      ]);
      await loadReports();
      navigate(`/reports/${report.id}/dashboard`);
    } catch (err: any) {
      console.error('Demo seed failed:', err);
      setErrorMessage('Failed to seed demo case.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="reports-landing-page">
      {/* Topbar Header */}
      <header className="topbar">
        <div className="topbar-left">
          <div className="sidebar-brand-icon-box" style={{ marginRight: '0.75rem' }}>
            <span style={{ fontSize: '1.4rem' }}>🛡️</span>
          </div>
          <span className="topbar-brand">UFDR Analysis Platform</span>
          <span className="topbar-sub">// MHA Smart Automation</span>
        </div>
        <div className="topbar-right">
          <div className="sys-status-badge">
            <span className="sys-pulse" />
            <span className="sys-text">SYS.OK</span>
          </div>
        </div>
      </header>

      <div className="shell-content">
        <div className="page-header">
          <div className="header-title-block">
            <span className="phase-tag">FORENSIC INTELLIGENCE // REPORT REPOSITORY</span>
            <h1 className="dash-title">UFDR Forensic Reports</h1>
            <p className="subtitle">
              Ingest a new cellular extraction report (XML / Text / UFDR format) or select an existing case to analyze.
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="shared-error-banner">
            <span>⚠️ {errorMessage}</span>
            <button className="btn-text-action" onClick={() => setErrorMessage(null)}>Dismiss</button>
          </div>
        )}

        {/* Upload Dropzone Card */}
        <div className="card upload-box-card">
          <div className="card-header-bar">
            <div className="ch-title">
              <h3>Upload Real UFDR Report</h3>
              <span className="text-small text-muted font-mono">Supports .XML, .UFDR, .TXT, .JSON extractions</span>
            </div>
            <button
              className="btn-cyber-outline"
              onClick={handleSeedDemoCase}
              disabled={uploading}
            >
              ⚡ Instant Demo Case
            </button>
          </div>

          <div
            className={`file-dropzone ${dragOver ? 'dropzone-active' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".xml,.ufdr,.txt,.json,.text"
              style={{ display: 'none' }}
            />
            <div className="dropzone-icon">📁</div>
            {selectedFile ? (
              <div className="selected-file-info">
                <span className="file-name font-mono">{selectedFile.name}</span>
                <span className="file-size font-mono">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              </div>
            ) : (
              <div className="dropzone-text">
                <span className="dropzone-main">Drag & Drop your UFDR XML File here</span>
                <span className="dropzone-sub">or click to browse files on your device</span>
              </div>
            )}
          </div>

          {selectedFile && (
            <div className="upload-actions-bar">
              <button
                className="btn-cyber-primary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleFileUploadSubmit();
                }}
                disabled={uploading}
              >
                <span className="btn-icon">🚀</span>
                <span>{uploading ? 'PARSING XML & INGESTING…' : 'INGEST REPORT FILE'}</span>
              </button>

              <button
                className="btn-cyber-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                disabled={uploading}
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {/* Ingested Reports Table */}
        {loading ? (
          <LoadingSpinner message="Retrieving ingested forensic reports…" />
        ) : reports.length === 0 ? (
          <EmptyState
            icon="📂"
            title="No reports ingested yet"
            description="Drag and drop a UFDR extraction file above to begin neural NER and symbolic correlation analysis."
          />
        ) : (
          <div className="card">
            <div className="table-header-row">
              <h3>Ingested Forensic Case Reports</h3>
              <span className="text-small text-muted font-mono">{reports.length} Report(s) Available</span>
            </div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Report ID</th>
                    <th>Filename</th>
                    <th>Pages</th>
                    <th>Pipeline Status</th>
                    <th>Created Timestamp</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id} className="clickable-row" onClick={() => navigate(`/reports/${r.id}/dashboard`)}>
                      <td className="font-mono text-cyan" style={{ fontWeight: 700 }}>{r.id}</td>
                      <td style={{ fontWeight: 600 }}>{r.filename}</td>
                      <td className="font-mono">{r.page_count} Pages</td>
                      <td>
                        <span className={`status-pill status-${r.status}`}>
                          {r.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="text-small text-muted font-mono">
                        {r.created_at ? r.created_at.slice(0, 19).replace('T', ' ') : 'N/A'}
                      </td>
                      <td>
                        <button
                          className="btn-cyber-outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/reports/${r.id}/dashboard`);
                          }}
                        >
                          Open Dashboard →
                        </button>
                      </td>
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
