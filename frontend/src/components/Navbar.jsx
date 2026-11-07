import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { BookOpen, LogOut, User, Sparkles, Settings, Zap } from "lucide-react";
import AzureConfigModal from "./AzureConfigModal";
import api from "../services/api";

export default function Navbar({ activeTab, setActiveTab, docCount = 0 }) {
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

  const userInitials = user?.username ? user.username.slice(0, 2).toUpperCase() : "U";

  return (
    <>
      <header className="navbar">
        <div className="navbar-container">
          <div className="brand" onClick={() => setActiveTab("documents")}>
            <div className="brand-icon">
              <BookOpen size={22} color="#ffffff" />
            </div>
            <div className="brand-text">
              <div className="brand-title-row">
                <span className="brand-title">DocuMind RAG</span>
                <span className="brand-live-pill">v2.0 • Live</span>
              </div>
              <span className="brand-subtitle">Azure OpenAI Document Intelligence</span>
            </div>
          </div>

          <nav className="nav-links">
            <button
              className={`nav-btn ${activeTab === "documents" ? "active" : ""}`}
              onClick={() => setActiveTab("documents")}
            >
              <span>Documents</span>
              {typeof docCount === "number" && docCount > 0 && (
                <span className="nav-count-badge">{docCount}</span>
              )}
            </button>
            <button
              className={`nav-btn ${activeTab === "chat" ? "active" : ""}`}
              onClick={() => setActiveTab("chat")}
            >
              <Sparkles size={15} style={{ marginRight: 6 }} />
              <span>RAG Chat</span>
            </button>
          </nav>

          <div className="nav-right">
            {/* Azure OpenAI Live Status Pill */}
            <button
              className={`azure-status-pill ${
                azureConfig?.is_configured ? "connected" : "unconfigured"
              }`}
              onClick={() => setIsAzureModalOpen(true)}
              title="Click to view or update Azure OpenAI configuration"
            >
              <span className="status-dot"></span>
              <Zap size={14} />
              <span>
                {azureConfig?.is_configured
                  ? `Azure: ${azureConfig.deployment_name}`
                  : "Connect Azure OpenAI"}
              </span>
            </button>

            <div className="nav-user">
              <div className="user-avatar-circle" title={`Logged in as ${user?.username}`}>
                {userInitials}
              </div>
              <span className="user-display-name">{user?.username}</span>
              <button className="logout-btn" onClick={logout} title="Sign Out">
                <LogOut size={15} />
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
