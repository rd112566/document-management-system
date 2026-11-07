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
  ExternalLink,
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
    if (window.confirm("Clear conversation history?")) {
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

  const suggestedQueries = [
    "What are the main topics discussed?",
    "Summarize the key requirements or conclusions.",
    "Are there any specific dates, numbers, or deadlines mentioned?",
  ];

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
            <option value="">🌐 All Documents (Multi-doc RAG)</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                📄 {d.original_name} ({d.page_count}p)
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
            <h3>Ask anything about your documents</h3>
            <p>
              I will search your vector embeddings and generate an accurate answer
              strictly backed by page-level citations.
            </p>
            <div className="suggestions-list">
              {suggestedQueries.map((query, i) => (
                <button
                  key={i}
                  className="suggestion-chip"
                  onClick={() => {
                    setInput(query);
                  }}
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
                      <span>Retrieving chunks & generating answer...</span>
                    </div>
                  ) : (
                    <>
                      <div className="bot-msg-meta">
                        <span className="model-tag">⚡ {msg.model_used || "gpt-5.6-luna (Azure OpenAI)"}</span>
                      </div>
                      <p className="answer-text">{msg.answer}</p>

                      {/* Citations Box */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="citations-box">
                          <div className="citations-header">
                            <BookOpen size={14} />
                            <span>Sources & Citations:</span>
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
                                      <button className="expand-btn">
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
              : "Ask across all uploaded documents..."
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
