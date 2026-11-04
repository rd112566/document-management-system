import React from "react";
import { useAuth } from "../context/AuthContext";
import { BookOpen, LogOut, User, Sparkles } from "lucide-react";

export default function Navbar({ activeTab, setActiveTab }) {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="brand" onClick={() => setActiveTab("documents")}>
          <div className="brand-icon">
            <BookOpen size={24} color="#ffffff" />
          </div>
          <div className="brand-text">
            <span className="brand-title">DocuMind RAG</span>
            <span className="brand-subtitle">Intelligent Document System</span>
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
    </header>
  );
}
