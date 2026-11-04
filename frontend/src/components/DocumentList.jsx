import React, { useState } from "react";
import api from "../services/api";
import {
  FileText,
  Trash2,
  Edit2,
  Download,
  Sparkles,
  MessageSquare,
  Check,
  X,
  Layers,
  Calendar,
} from "lucide-react";

export default function DocumentList({
  documents,
  loading,
  onRefresh,
  onSelectForChat,
}) {
  const [editingId, setEditingId] = useState(null);
  const [newName, setNewName] = useState("");
  const [summaryData, setSummaryData] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const startRename = (doc) => {
    setEditingId(doc.id);
    setNewName(doc.original_name);
  };

  const saveRename = async (id) => {
    if (!newName.trim()) return;
    try {
      await api.put(`/api/documents/${id}/rename`, { new_name: newName });
      setEditingId(null);
      onRefresh();
    } catch (err) {
      alert("Failed to rename document");
    }
  };

  const handleDelete = async (id, name) => {
    if (window.confirm(`Are you sure you want to delete "${name}"? This removes all vector embeddings and chunks.`)) {
      try {
        await api.delete(`/api/documents/${id}`);
        onRefresh();
      } catch (err) {
        alert("Failed to delete document");
      }
    }
  };

  const handleDownload = (id) => {
    window.open(`http://127.0.0.1:8000/api/documents/${id}/download`, "_blank");
  };

  const handleGenerateSummary = async (id, name) => {
    setSummaryLoading(true);
    setSummaryData({ name, text: "Analyzing document chunks..." });
    try {
      const res = await api.post(`/api/documents/${id}/summary`);
      setSummaryData({ name, text: res.data.summary });
    } catch (err) {
      setSummaryData({ name, text: "Failed to generate summary." });
    } finally {
      setSummaryLoading(false);
    }
  };

  return (
    <div className="doc-list-container">
      <div className="doc-list-header">
        <div>
          <h3>My Knowledge Base</h3>
          <p>{documents.length} document{documents.length === 1 ? "" : "s"} indexed in ChromaDB</p>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} className="empty-icon" />
          <p>No documents uploaded yet.</p>
          <span>Upload your first PDF, DOCX, or TXT file above to get started!</span>
        </div>
      ) : (
        <div className="doc-grid">
          {documents.map((doc) => (
            <div key={doc.id} className="doc-card">
              <div className="doc-card-top">
                <span className={`file-badge ${doc.file_type}`}>
                  {doc.file_type.toUpperCase()}
                </span>
                <div className="doc-card-actions">
                  <button
                    className="icon-action-btn"
                    title="Download file"
                    onClick={() => handleDownload(doc.id)}
                  >
                    <Download size={16} />
                  </button>
                  <button
                    className="icon-action-btn"
                    title="Rename"
                    onClick={() => startRename(doc)}
                  >
                    <Edit2 size={16} />
                  </button>
                  <button
                    className="icon-action-btn delete"
                    title="Delete document & vectors"
                    onClick={() => handleDelete(doc.id, doc.original_name)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {editingId === doc.id ? (
                <div className="rename-inline">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    autoFocus
                  />
                  <button onClick={() => saveRename(doc.id)} title="Save">
                    <Check size={16} />
                  </button>
                  <button onClick={() => setEditingId(null)} title="Cancel">
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <h4 className="doc-title" title={doc.original_name}>
                  {doc.original_name}
                </h4>
              )}

              <div className="doc-meta">
                <span>
                  <Layers size={14} /> {doc.page_count} page{doc.page_count === 1 ? "" : "s"}
                </span>
                <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                <span>
                  <Calendar size={14} /> {new Date(doc.upload_date).toLocaleDateString()}
                </span>
              </div>

              <div className="doc-card-bottom">
                <button
                  className="card-secondary-btn"
                  onClick={() => handleGenerateSummary(doc.id, doc.original_name)}
                >
                  <Sparkles size={14} />
                  Summary
                </button>
                <button
                  className="card-primary-btn"
                  onClick={() => onSelectForChat(doc.id)}
                >
                  <MessageSquare size={14} />
                  Chat
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary Modal */}
      {summaryData && (
        <div className="modal-overlay" onClick={() => setSummaryData(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Sparkles size={20} color="#6366f1" />
                <h3>Document Summary</h3>
              </div>
              <button className="close-btn" onClick={() => setSummaryData(null)}>
                <X size={20} />
              </button>
            </div>
            <p className="modal-sub">Summary for: <strong>{summaryData.name}</strong></p>
            <div className="modal-content">
              {summaryLoading ? (
                <p>Generating intelligent summary...</p>
              ) : (
                <p className="summary-text">{summaryData.text}</p>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-primary" onClick={() => setSummaryData(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
