import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  BookOpen,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Lock,
  User,
  Mail,
  Eye,
  EyeOff,
  Zap,
  Shield,
  Layers,
  Sparkles,
} from "lucide-react";

export default function AuthModal() {
  const { login, signup } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        await login(username, password);
      } else {
        if (!email) {
          setError("Please provide a valid email address.");
          setLoading(false);
          return;
        }
        await signup(username, email, password);
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        "Authentication failed. Please verify your credentials or create a new account.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError("");
    setLoading(true);
    try {
      // First try logging in with demo user
      try {
        await login("demo_user", "DemoPassword123!");
      } catch (loginErr) {
        // If demo_user does not exist yet, sign up automatically
        await signup("demo_user", "demo@example.com", "DemoPassword123!");
      }
    } catch (err) {
      setError("Unable to launch demo session. Please try standard login or signup.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-fullscreen">
      <div className="auth-hero-container">
        {/* Left Side: Brand Showcase & Value Proposition */}
        <div className="auth-hero-panel">
          <div className="hero-branding">
            <div className="hero-logo-box">
              <BookOpen size={30} color="#ffffff" />
            </div>
            <div>
              <h1 className="hero-app-title">DocuMind RAG</h1>
              <span className="hero-app-tag">Enterprise Document Intelligence</span>
            </div>
          </div>

          <div className="hero-headline-group">
            <h2>
              Transform static documents into <span className="text-gradient">intelligent conversations</span>.
            </h2>
            <p>
              Extract tables, multi-column pages, and structured data across PDF, DOCX, Excel, and JSON.
              Answer questions with verifiable citations powered by <strong>Azure OpenAI GPT models</strong>.
            </p>
          </div>

          <div className="hero-feature-list">
            <div className="feature-item">
              <div className="feature-icon-badge">
                <Zap size={18} />
              </div>
              <div className="feature-text">
                <strong>Azure OpenAI GPT Powered</strong>
                <span>Direct integration with deployments like GPT-5.6-Luna, GPT-4o, and GPT-4.</span>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon-badge">
                <Layers size={18} />
              </div>
              <div className="feature-text">
                <strong>Multi-Format Ingestion Engine</strong>
                <span>Accurate sentence-aware chunking for PDF, Word, Spreadsheets, CSV, and JSON.</span>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon-badge">
                <Shield size={18} />
              </div>
              <div className="feature-text">
                <strong>Isolated Vector Stores &amp; Strict Citations</strong>
                <span>ChromaDB isolated embeddings with transparent page numbers and snippet proofs.</span>
              </div>
            </div>
          </div>

          <div className="hero-badges-row">
            <span className="hero-pill">⚡ ChromaDB Persistent</span>
            <span className="hero-pill">🔒 AES-256 JWT</span>
            <span className="hero-pill">📄 100% Grounded RAG</span>
          </div>
        </div>

        {/* Right Side: Auth Card Form */}
        <div className="auth-form-panel">
          <div className="auth-card-modern">
            <div className="auth-card-header">
              <h3>{isLogin ? "Sign In to Your Workspace" : "Create Enterprise Account"}</h3>
              <p>
                {isLogin
                  ? "Access your document repository and continue your RAG queries"
                  : "Start extracting and indexing documents with Azure OpenAI in seconds"}
              </p>
            </div>

            {/* Segmented Switcher */}
            <div className="auth-segmented-tabs">
              <button
                type="button"
                className={`tab-btn ${isLogin ? "active" : ""}`}
                onClick={() => {
                  setIsLogin(true);
                  setError("");
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`tab-btn ${!isLogin ? "active" : ""}`}
                onClick={() => {
                  setIsLogin(false);
                  setError("");
                }}
              >
                Create Account
              </button>
            </div>

            {/* Quick Demo Button */}
            <button
              type="button"
              className="demo-quick-btn"
              onClick={handleDemoLogin}
              disabled={loading}
              title="Instantly sign in with pre-configured demo credentials"
            >
              <Sparkles size={16} />
              <span>Instant Demo Access (1-Click)</span>
            </button>

            <div className="auth-divider">
              <span>or continue with credentials</span>
            </div>

            {error && (
              <div className="auth-error-banner">
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form-modern">
              <div className="form-field">
                <label>Username</label>
                <div className="input-field-wrapper">
                  <User size={18} className="field-icon" />
                  <input
                    type="text"
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
              </div>

              {!isLogin && (
                <div className="form-field">
                  <label>Email Address</label>
                  <div className="input-field-wrapper">
                    <Mail size={18} className="field-icon" />
                    <input
                      type="email"
                      placeholder="name@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>
              )}

              <div className="form-field">
                <label>Password</label>
                <div className="input-field-wrapper">
                  <Lock size={18} className="field-icon" />
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button type="submit" className="auth-submit-btn" disabled={loading}>
                {loading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <span>{isLogin ? "Sign In" : "Get Started"}</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-footer-prompt">
              <span>{isLogin ? "New to DocuMind?" : "Already registered?"}</span>
              <button
                type="button"
                className="link-switch-btn"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError("");
                }}
              >
                {isLogin ? "Create an account" : "Sign in here"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
