import React, { useState } from "react";
import api from "../services/api";
import { UploadCloud, CheckCircle, AlertTriangle, FileText, Loader2 } from "lucide-react";

export default function DocumentUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState({ type: "", text: "" });

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      const ext = selected.name.split(".").pop().toLowerCase();
      if (!["pdf", "docx", "doc", "txt"].includes(ext)) {
        setStatusMsg({
          type: "error",
          text: "Invalid file format. Please upload PDF, DOCX, or TXT documents.",
        });
        setFile(null);
        return;
      }
      setFile(selected);
      setStatusMsg({ type: "", text: "" });
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(15);
    setStatusMsg({ type: "info", text: "Uploading and processing text with OCR & metadata..." });

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.post("/api/documents/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(Math.min(percent, 85));
        },
      });

      setProgress(100);
      setStatusMsg({
        type: "success",
        text: `"${res.data.original_name}" uploaded & indexed (${res.data.chunks_indexed} chunks created)!`,
      });
      setFile(null);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        (err.response?.status === 401
          ? "You are not logged in on the live site. Please sign up or log in first."
          : "Upload failed. The server might be waking up; please try again in a few seconds.");
      setStatusMsg({ type: "error", text: detail });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-card">
      <div className="upload-header">
        <h3>Upload Document</h3>
        <p>Supports PDF (PyMuPDF & OCR), DOCX, and TXT files</p>
      </div>

      <div
        className={`dropzone ${file ? "has-file" : ""}`}
        onClick={() => document.getElementById("file-input").click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".pdf,.docx,.doc,.txt"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />

        {file ? (
          <div className="selected-file-preview">
            <FileText size={38} className="file-icon" />
            <div className="file-info">
              <span className="file-name">{file.name}</span>
              <span className="file-size">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
            </div>
          </div>
        ) : (
          <div className="dropzone-content">
            <UploadCloud size={44} className="upload-icon" />
            <p className="primary-text">Click or drag & drop to choose a document</p>
            <p className="sub-text">PDF, DOCX, or TXT up to 50MB</p>
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
          {uploading ? "Extracting & Indexing..." : "Process & Embed Document"}
        </button>
      </div>
    </div>
  );
}
