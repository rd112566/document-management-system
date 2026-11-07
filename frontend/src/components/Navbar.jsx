import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { BookOpen, LogOut, User, Sparkles, Settings, Zap } from "lucide-react";
import AzureConfigModal from "./AzureConfigModal";
import api from "../services/api";

export default function Navbar({ activeTab, setActiveTab }) {
  const { user, logout } = useAuth();
  const [isAzureModalOpen, setIsAzureModalOpen] = useState(false);
  const [azureConfig, setAzureConfig] = useState(null);

  const fetchAzureStatus = async () => {
    if (!user) return;
    try {
      const res = await api.get("/api/azure/config");
      setAzureConfig(res.data);
    } catch (err) {
      console.error("Failed to fetch Azure status", err);
    }
  };

  useEffect(() => {
    fetchAzureStatus();
  }, [user]);

  return (
    <>
      <header className="navbar">
        <div className="navbar-container">
          <div className="brand" onClick={() => setActiveTab("documents")}>
            <div className="brand-icon">
              <BookOpen size={24} color="#ffffff" />
            </div>
            <div className="brand-text">
              <span className="brand-title">DocuMind RAG</span>
              <span className="brand-subtitle">Document Intelligence &amp; QA</span>
            </div>
          </div>

          <nav className="nav-links">
            <button
              className={`nav-btn ${activeTab === "documents" ? "active" : ""}`}
              onClick={() => setActiveTab("documents")}
            >
              Documents
            </button>
            <button
              className={`nav-btn ${activeTab === "chat" ? "active" : ""}`}
              onClick={() => setActiveTab("chat")}
            >
              <Sparkles size={16} style={{ marginRight: 6 }} />
              RAG Chat
            </button>
          </nav>

          <div className="nav-right">
            {/* Azure OpenAI Status Pill */}
            <button
              className={`azure-status-pill ${
                azureConfig?.is_configured ? "connected" : "unconfigured"
              }`}
              onClick={() => setIsAzureModalOpen(true)}
              title="Click to configure Azure OpenAI deployment"
            >
              <Zap size={14} />
              <span>
                {azureConfig?.is_configured
                  ? `Azure: ${azureConfig.deployment_name}`
                  : "Azure OpenAI Setup"}
              </span>
              <span className="status-dot"></span>
            </button>

            <div className="nav-user">
              <div className="user-badge">
                <User size={16} />
                <span className="username">{user?.username}</span>
              </div>
              <button className="logout-btn" onClick={logout} title="Sign Out">
                <LogOut size={16} />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <AzureConfigModal
        isOpen={isAzureModalOpen}
        onClose={() => setIsAzureModalOpen(false)}
        onConfigSaved={(updated) => setAzureConfig(updated)}
      />
    </>
  );
}
