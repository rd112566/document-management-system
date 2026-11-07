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
  Eye,
  Loader2,
} from "lucide-react";

export default function DocumentList({
  documents,
  loading,
  onRefresh,
  onSelectForChat,
}) {
  const [editingId, setEditingId] = useState(null);
  const [newName, setNewName] = useState("");
  
  // Summary modal state
  const [summaryData, setSummaryData] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Chunks preview modal state
  const [chunksData, setChunksData] = useState(null);
  const [chunksLoading, setChunksLoading] = useState(false);

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
    if (
      window.confirm(
        `Are you sure you want to delete "${name}"? This removes the file and all vector embeddings from ChromaDB.`
      )
    ) {
      try {
        await api.delete(`/api/documents/${id}`);
        onRefresh();
      } catch (err) {
        alert("Failed to delete document");
      }
    }
  };

  const handleDownload = (id) => {
    const baseUrl = api.defaults.baseURL || "http://127.0.0.1:8000";
    window.open(`${baseUrl}/api/documents/${id}/download`, "_blank");
  };

  const handleGenerateSummary = async (id, name) => {
    setSummaryLoading(true);
    setSummaryData({ name, text: "Generating summary using Azure OpenAI GPT..." });
    try {
      const res = await api.post(`/api/documents/${id}/summary`);
      setSummaryData({ name, text: res.data.summary });
    } catch (err) {
      setSummaryData({ name, text: "Failed to generate summary." });
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleViewChunks = async (id, name) => {
    setChunksLoading(true);
    setChunksData({ name, chunks: [] });
    try {
      const res = await api.get(`/api/documents/${id}/chunks`);
      setChunksData({ name, chunks: res.data.chunks, total: res.data.total_chunks });
    } catch (err) {
      alert("Failed to load document chunks");
      setChunksData(null);
    } finally {
      setChunksLoading(false);
    }
  };

  return (
    <div className="doc-list-container">
      <div className="doc-list-header">
        <div>
          <h3>My Knowledge Base</h3>
          <p>
            {documents.length} document{documents.length === 1 ? "" : "s"} indexed in ChromaDB for Azure OpenAI RAG
          </p>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} className="empty-icon" />
          <p>No documents uploaded yet.</p>
          <span>Upload your first document above (PDF, DOCX, TXT, Excel, CSV, JSON) to get started!</span>
        </div>
      ) : (
        <div className="doc-grid">
          {documents.map((doc) => (
            <div key={doc.id} className="doc-card">
              <div className="doc-card-top">
                <span className={`file-badge ${doc.file_type.toLowerCase()}`}>
                  {doc.file_type.toUpperCase()}
                </span>
                <div className="doc-card-actions">
                  <button
                    className="icon-action-btn"
                    title="Inspect extracted chunks"
                    onClick={() => handleViewChunks(doc.id, doc.original_name)}
                  >
                    <Eye size={15} />
                  </button>
                  <button
                    className="icon-action-btn"
                    title="Download file"
                    onClick={() => handleDownload(doc.id)}
                  >
                    <Download size={15} />
                  </button>
                  <button
                    className="icon-action-btn"
                    title="Rename"
                    onClick={() => startRename(doc)}
                  >
                    <Edit2 size={15} />
                  </button>
                  <button
                    className="icon-action-btn delete"
                    title="Delete document & vectors"
                    onClick={() => handleDelete(doc.id, doc.original_name)}
                  >
                    <Trash2 size={15} />
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
                  <Layers size={14} /> {doc.page_count} {doc.page_count === 1 ? "section/page" : "pages"}
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
                <h3>Azure OpenAI Executive Summary</h3>
              </div>
              <button className="close-btn" onClick={() => setSummaryData(null)}>
                <X size={20} />
              </button>
            </div>
            <p className="modal-sub">
              Document: <strong>{summaryData.name}</strong>
            </p>
            <div className="modal-content">
              {summaryLoading ? (
                <div className="modal-loading">
                  <Loader2 className="spin" size={20} />
                  <span>Synthesizing document with Azure OpenAI...</span>
                </div>
              ) : (
                <div className="summary-markdown">
                  <p style={{ whiteSpace: "pre-wrap" }}>{summaryData.text}</p>
                </div>
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

      {/* Extracted Chunks Inspection Modal */}
      {chunksData && (
        <div className="modal-overlay" onClick={() => setChunksData(null)}>
          <div className="modal-box chunks-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Eye size={20} color="#3b82f6" />
                <h3>Extracted Text Chunks &amp; Index</h3>
              </div>
              <button className="close-btn" onClick={() => setChunksData(null)}>
                <X size={20} />
              </button>
            </div>
            <p className="modal-sub">
              Document: <strong>{chunksData.name}</strong> ({chunksData.total || 0} chunks in vector index)
            </p>
            <div className="modal-content chunks-list">
              {chunksLoading ? (
                <div className="modal-loading">
                  <Loader2 className="spin" size={20} />
                  <span>Loading extracted chunks...</span>
                </div>
              ) : chunksData.chunks?.length === 0 ? (
                <p>No chunks found for this document.</p>
              ) : (
                chunksData.chunks.map((c, i) => (
                  <div key={i} className="chunk-card">
                    <div className="chunk-header">
                      <span className="chunk-badge">Page {c.page}</span>
                      <span className="chunk-index">Chunk #{c.chunk_index}</span>
                    </div>
                    <p className="chunk-text">{c.text}</p>
                  </div>
                ))
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-primary" onClick={() => setChunksData(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
