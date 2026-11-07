import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import AuthModal from "./components/AuthModal";
import DocumentUpload from "./components/DocumentUpload";
import DocumentList from "./components/DocumentList";
import ChatInterface from "./components/ChatInterface";
import api from "./services/api";
import "./App.css";

function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState("documents");
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState(null);

  const fetchDocuments = async () => {
    if (!user) return;
    setDocsLoading(true);
    try {
      const res = await api.get("/api/documents");
      setDocuments(res.data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    } finally {
      setDocsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchDocuments();
    }
  }, [user]);

  // Live browser tab title synchronization
  useEffect(() => {
    if (!user) {
      document.title = "Sign In — DocuMind RAG";
      return;
    }
    if (activeTab === "chat") {
      const selectedDoc = documents.find((d) => d.id === selectedDocId);
      if (selectedDoc) {
        document.title = `💬 QA: ${selectedDoc.original_name} — DocuMind RAG`;
      } else {
        document.title = "💬 Multi-Doc RAG Chat — DocuMind RAG";
      }
    } else {
      document.title = `📁 Knowledge Base (${documents.length}) — DocuMind RAG`;
    }
  }, [user, activeTab, selectedDocId, documents]);

  if (authLoading) {
    return (
      <div className="app-loading-screen">
        <div className="loading-spinner-large"></div>
        <p>Initializing DocuMind RAG Intelligence Engine...</p>
      </div>
    );
  }

  if (!user) {
    return <AuthModal />;
  }

  const handleSelectForChat = (docId) => {
    setSelectedDocId(docId);
    setActiveTab("chat");
  };

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        docCount={documents.length}
      />

      <main className="main-content">
        {activeTab === "documents" ? (
          <div className="documents-view">
            <DocumentUpload onUploadSuccess={fetchDocuments} />
            <DocumentList
              documents={documents}
              loading={docsLoading}
              onRefresh={fetchDocuments}
              onSelectForChat={handleSelectForChat}
            />
          </div>
        ) : (
          <div className="chat-view">
            <ChatInterface
              documents={documents}
              selectedDocId={selectedDocId}
              setSelectedDocId={setSelectedDocId}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
}
