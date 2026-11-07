import React, { useState } from "react";
import api from "../services/api";
import {
  UploadCloud,
  CheckCircle,
  AlertTriangle,
  FileText,
  Loader2,
  FileSpreadsheet,
  FileCode,
} from "lucide-react";

const SUPPORTED_EXTS = ["pdf", "docx", "doc", "txt", "md", "markdown", "csv", "tsv", "xlsx", "xls", "json"];

export default function DocumentUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState({ type: "", text: "" });

  const validateAndSetFile = (selected) => {
    if (!selected) return;
    const ext = selected.name.split(".").pop().toLowerCase();
    if (!SUPPORTED_EXTS.includes(ext)) {
      setStatusMsg({
        type: "error",
        text: `Unsupported format ('.${ext}'). Please upload PDF, Word (DOCX), Text, Markdown, Excel, CSV, or JSON documents.`,
      });
      setFile(null);
      return;
    }
    setFile(selected);
    setStatusMsg({ type: "", text: "" });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(15);
    setStatusMsg({
      type: "info",
      text: "Uploading document, extracting text & generating vector embeddings in ChromaDB...",
    });

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.post("/api/documents/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(Math.min(percent, 85));
          }
        },
      });

      setProgress(100);
      setStatusMsg({
        type: "success",
        text: `"${res.data.original_name}" uploaded and indexed successfully (${res.data.chunks_indexed} chunks created)!`,
      });
      setFile(null);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        (err.response?.status === 401
          ? "You are not logged in. Please sign up or log in first."
          : "Upload failed. Please ensure the backend server is running and try again.");
      setStatusMsg({ type: "error", text: detail });
    } finally {
      setUploading(false);
    }
  };

  const getFileIcon = (filename) => {
    const ext = filename?.split(".").pop().toLowerCase();
    if (["xlsx", "xls", "csv", "tsv"].includes(ext)) {
      return <FileSpreadsheet size={38} className="file-icon" color="#10b981" />;
    }
    if (["json", "md"].includes(ext)) {
      return <FileCode size={38} className="file-icon" color="#f59e0b" />;
    }
    return <FileText size={38} className="file-icon" color="#6366f1" />;
  };

  return (
    <div className="upload-card">
      <div className="upload-header">
        <h3>Upload Documents</h3>
        <p>
          Extract text and index into ChromaDB for Q&amp;A retrieval with Azure OpenAI GPT models
        </p>
      </div>

      <div
        className={`dropzone ${file ? "has-file" : ""} ${isDragging ? "dragging" : ""}`}
        onClick={() => document.getElementById("file-input").click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          id="file-input"
          type="file"
          accept=".pdf,.docx,.doc,.txt,.md,.markdown,.csv,.tsv,.xlsx,.xls,.json"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />

        {file ? (
          <div className="selected-file-preview">
            {getFileIcon(file.name)}
            <div className="file-info">
              <span className="file-name">{file.name}</span>
              <span className="file-size">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
            </div>
          </div>
        ) : (
          <div className="dropzone-content">
            <UploadCloud size={44} className="upload-icon" />
            <p className="primary-text">
              {isDragging ? "Drop your file here!" : "Click or drag & drop to upload a document"}
            </p>
            <p className="sub-text">
              Supports <strong>PDF, Word (DOCX), Text, Markdown, Excel, CSV, JSON</strong> (up to 50MB)
            </p>
          </div>
        )}
      </div>

      {uploading && (
        <div className="progress-container">
          <div className="progress-bar-bg">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="progress-text">{progress}% complete</span>
        </div>
      )}

      {statusMsg.text && (
        <div className={`status-banner ${statusMsg.type}`}>
          {statusMsg.type === "success" && <CheckCircle size={18} />}
          {statusMsg.type === "error" && <AlertTriangle size={18} />}
          {statusMsg.type === "info" && <Loader2 size={18} className="spin" />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      <div className="upload-actions">
        <button
          className="btn-primary"
          onClick={handleUpload}
          disabled={!file || uploading}
        >
          {uploading ? "Extracting & Indexing..." : "Process & Index Document"}
        </button>
      </div>
    </div>
  );
}
