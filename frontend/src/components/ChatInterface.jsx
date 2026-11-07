import React, { useState, useEffect, useRef } from "react";
import api from "../services/api";
import {
  Send,
  Sparkles,
  Bot,
  User,
  BookOpen,
  Trash2,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  Copy,
  Check,
  Zap,
} from "lucide-react";

export default function ChatInterface({
  documents,
  selectedDocId,
  setSelectedDocId,
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState({});
  const [copiedId, setCopiedId] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchHistory();
  }, [selectedDocId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchHistory = async () => {
    try {
      const params = selectedDocId ? { document_id: selectedDocId } : {};
      const res = await api.get("/api/chat/history", { params });
      setMessages(res.data);
    } catch (err) {
      console.error("Failed to load chat history", err);
    }
  };

  const clearHistory = async () => {
    if (window.confirm("Clear conversation history for this scope?")) {
      try {
        const params = selectedDocId ? { document_id: selectedDocId } : {};
        await api.delete("/api/chat/history", { params });
        setMessages([]);
      } catch (err) {
        alert("Failed to clear chat history");
      }
    }
  };

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    const userQuestion = input.trim();
    setInput("");

    // Optimistic UI update
    const tempId = Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        question: userQuestion,
        answer: null, // Loading indicator for this message
        citations: [],
      },
    ]);
    setLoading(true);

    try {
      const res = await api.post("/api/chat", {
        question: userQuestion,
        document_id: selectedDocId || null,
      });

      setMessages((prev) =>
        prev.map((m) => (m.id === tempId ? res.data : m))
      );
    } catch (err) {
      const detail = err.response?.data?.detail || "Error querying knowledge base.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? {
                ...m,
                answer: `⚠️ Error: ${detail}`,
                citations: [],
                model_used: "Error",
              }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const toggleCitation = (msgId, index) => {
    const key = `${msgId}_${index}`;
    setExpandedCitations((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getSuggestedQueries = () => {
    if (!selectedDocId) {
      return [
        "What are the main topics and objectives discussed in the uploaded documents?",
        "Summarize the key requirements, policies, or conclusions.",
        "Are there any specific dates, numbers, figures, or deadlines mentioned?",
      ];
    }
    const currentDoc = documents.find((d) => d.id === selectedDocId);
    const docName = currentDoc?.original_name?.toLowerCase() || "";

    if (docName.includes("quantum")) {
      return [
        "What did Google Quantum AI demonstrate in 2019?",
        "What speedup does Grover's algorithm provide?",
        "What is Shor's algorithm used for?",
        "How many physical qubits are needed per logical qubit?",
      ];
    }
    if (docName.includes("policy") || docName.includes("governance")) {
      return [
        "What encryption standard is required by the AI policy?",
        "How long can authentication tokens last before expiring?",
        "Does the policy allow cross-tenant data access?",
        "Summarize the security and compliance requirements.",
      ];
    }
    if (docName.includes("requirement") || docName.includes("project")) {
      return [
        "What are the three main deliverables of the project?",
        "What is the project budget and deadline?",
        "What vector store is specified in the requirements?",
        "What file formats must the document extraction support?",
      ];
    }
    return [
      `Summarize the key takeaways of ${currentDoc?.original_name || "this document"}.`,
      "What are the most important conclusions or recommendations?",
      "List all specific metrics, numbers, and dates mentioned.",
    ];
  };

  const suggestedQueries = getSuggestedQueries();

  return (
    <div className="chat-container">
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-scope">
          <label>Query Scope:</label>
          <select
            value={selectedDocId || ""}
            onChange={(e) =>
              setSelectedDocId(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">🌐 All Uploaded Documents (Multi-doc RAG)</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                📄 {d.original_name} ({d.page_count} {d.page_count === 1 ? "page" : "pages"})
              </option>
            ))}
          </select>
        </div>

        {messages.length > 0 && (
          <button className="clear-btn" onClick={clearHistory} title="Clear history">
            <Trash2 size={16} />
            <span>Clear History</span>
          </button>
        )}
      </div>

      {/* Messages Thread */}
      <div className="messages-thread">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <Bot size={44} />
            </div>
            <h3>Ask questions about your uploaded documents</h3>
            <p>
              The system queries ChromaDB vector embeddings and uses <strong>Azure OpenAI GPT models</strong> to
              extract and synthesize answers with precise page-level citations.
            </p>
            <div className="suggestions-list">
              {suggestedQueries.map((query, i) => (
                <button
                  key={i}
                  className="suggestion-chip"
                  onClick={() => setInput(query)}
                >
                  <Sparkles size={14} />
                  <span>{query}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="message-group">
              {/* User Question */}
              <div className="message user-msg">
                <div className="msg-avatar user">
                  <User size={16} />
                </div>
                <div className="msg-body">
                  <p>{msg.question}</p>
                </div>
              </div>

              {/* Assistant Answer */}
              <div className="message bot-msg">
                <div className="msg-avatar bot">
                  <Bot size={16} />
                </div>
                <div className="msg-body">
                  {msg.answer === null ? (
                    <div className="generating-loader">
                      <Loader2 size={18} className="spin" />
                      <span>Fetching document context &amp; querying Azure OpenAI GPT...</span>
                    </div>
                  ) : (
                    <>
                      <div className="bot-msg-meta">
                        <span className="model-tag">
                          <Zap size={13} style={{ marginRight: 4 }} />
                          {msg.model_used || "gpt-4o (Azure OpenAI)"}
                        </span>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(msg.answer, msg.id)}
                          title="Copy answer"
                        >
                          {copiedId === msg.id ? (
                            <>
                              <Check size={13} color="#10b981" />
                              <span style={{ color: "#10b981" }}>Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy size={13} />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>

                      <div className="answer-text">
                        <p style={{ whiteSpace: "pre-wrap" }}>{msg.answer}</p>
                      </div>

                      {/* Citations Box */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="citations-box">
                          <div className="citations-header">
                            <BookOpen size={14} />
                            <span>Sources &amp; Citations:</span>
                          </div>
                          <div className="citations-list">
                            {msg.citations.map((cite, idx) => {
                              const isExp = expandedCitations[`${msg.id}_${idx}`];
                              return (
                                <div key={idx} className="citation-badge">
                                  <div
                                    className="citation-main"
                                    onClick={() => toggleCitation(msg.id, idx)}
                                  >
                                    <FileText size={13} />
                                    <span className="cite-doc">
                                      {cite.document_name}
                                    </span>
                                    <span className="cite-page">
                                      Page {cite.page}
                                    </span>
                                    {cite.snippet && (
                                      <button className="expand-btn" type="button">
                                        {isExp ? (
                                          <ChevronUp size={14} />
                                        ) : (
                                          <ChevronDown size={14} />
                                        )}
                                      </button>
                                    )}
                                  </div>
                                  {isExp && cite.snippet && (
                                    <div className="citation-snippet">
                                      "{cite.snippet}"
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} className="chat-input-bar">
        <input
          type="text"
          placeholder={
            selectedDocId
              ? "Ask a question about the selected document..."
              : "Ask a question across all uploaded documents..."
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="send-btn"
          disabled={!input.trim() || loading}
        >
          {loading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
        </button>
      </form>
    </div>
  );
}
