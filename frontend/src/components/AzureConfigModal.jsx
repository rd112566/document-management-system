import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  Settings,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Server,
  Zap,
  Info,
} from "lucide-react";

export default function AzureConfigModal({ isOpen, onClose, onConfigSaved }) {
  const [endpoint, setEndpoint] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [deploymentName, setDeploymentName] = useState("gpt-4o");
  const [apiVersion, setApiVersion] = useState("2024-08-01-preview");
  const [showKey, setShowKey] = useState(false);
  const [maskedKey, setMaskedKey] = useState("");

  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchConfig();
      setTestResult(null);
      setSaveStatus(null);
    }
  }, [isOpen]);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/azure/config");
      setEndpoint(res.data.endpoint || "");
      setDeploymentName(res.data.deployment_name || "gpt-4o");
      setApiVersion(res.data.api_version || "2024-08-01-preview");
      setMaskedKey(res.data.masked_api_key || "");
    } catch (err) {
      console.error("Failed to load Azure config", err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const payload = {
        endpoint: endpoint.trim(),
        api_key: apiKey.trim() || undefined,
        deployment_name: deploymentName.trim(),
        api_version: apiVersion.trim(),
      };
      const res = await api.post("/api/azure/test-connection", payload);
      setTestResult(res.data);
    } catch (err) {
      setTestResult({
        success: false,
        error: err.response?.data?.detail || "Network request failed while pinging Azure OpenAI.",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaveStatus({ type: "loading", message: "Saving settings..." });

    try {
      const payload = {
        endpoint: endpoint.trim(),
        deployment_name: deploymentName.trim(),
        api_version: apiVersion.trim(),
      };
      if (apiKey.trim()) {
        payload.api_key = apiKey.trim();
      }

      const res = await api.post("/api/azure/config", payload);
      setSaveStatus({ type: "success", message: "Configuration saved successfully!" });
      setApiKey("");
      setMaskedKey(res.data.config.masked_api_key);
      if (onConfigSaved) onConfigSaved(res.data.config);
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      setSaveStatus({
        type: "error",
        message: err.response?.data?.detail || "Failed to save Azure configuration.",
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box azure-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div className="azure-icon-badge">
              <Zap size={20} color="#3b82f6" />
            </div>
            <div>
              <h3>Azure OpenAI Configuration</h3>
              <p className="azure-modal-subtitle">
                Configure your deployed GPT models (GPT-4o, GPT-4o-mini, GPT-4, GPT-3.5)
              </p>
            </div>
          </div>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {loading ? (
          <div className="modal-loading">
            <Loader2 className="spin" size={24} />
            <span>Loading Azure OpenAI settings...</span>
          </div>
        ) : (
          <form onSubmit={handleSave} className="azure-form">
            <div className="form-group">
              <label>
                Azure OpenAI Endpoint:
                <span className="field-hint">From Azure Portal &gt; Keys &amp; Endpoint</span>
              </label>
              <input
                type="text"
                placeholder="https://your-resource-name.openai.azure.com/"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>
                Azure OpenAI API Key:
                {maskedKey && (
                  <span className="field-hint">Current: {maskedKey} (leave blank to keep)</span>
                )}
              </label>
              <div className="input-with-icon">
                <input
                  type={showKey ? "text" : "password"}
                  placeholder={maskedKey ? "Enter new key to replace" : "Enter Azure OpenAI API Key"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <button
                  type="button"
                  className="icon-toggle-btn"
                  onClick={() => setShowKey(!showKey)}
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group flex-1">
                <label>
                  GPT Deployment Name:
                  <span className="field-hint">As named in Azure OpenAI Studio</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. gpt-4o, gpt-4o-mini, gpt-4"
                  value={deploymentName}
                  onChange={(e) => setDeploymentName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group flex-1">
                <label>
                  API Version:
                  <span className="field-hint">e.g. 2024-08-01-preview</span>
                </label>
                <input
                  type="text"
                  placeholder="2024-08-01-preview"
                  value={apiVersion}
                  onChange={(e) => setApiVersion(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* Test Connection Banner */}
            {testResult && (
              <div
                className={`azure-test-banner ${
                  testResult.success ? "success" : "error"
                }`}
              >
                {testResult.success ? (
                  <>
                    <CheckCircle2 size={18} />
                    <div className="test-banner-content">
                      <strong>Connection Successful!</strong>
                      <span>
                        Latency: {testResult.latency_ms}ms | Deployment: {testResult.deployment}
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <AlertCircle size={18} />
                    <div className="test-banner-content">
                      <strong>Connection Failed</strong>
                      <span>{testResult.error}</span>
                    </div>
                  </>
                )}
              </div>
            )}

            {saveStatus && (
              <div className={`azure-save-banner ${saveStatus.type}`}>
                {saveStatus.type === "loading" && <Loader2 size={16} className="spin" />}
                {saveStatus.type === "success" && <CheckCircle2 size={16} />}
                {saveStatus.type === "error" && <AlertCircle size={16} />}
                <span>{saveStatus.message}</span>
              </div>
            )}

            <div className="modal-footer azure-footer">
              <button
                type="button"
                className="btn-secondary test-btn"
                onClick={handleTestConnection}
                disabled={testing}
              >
                {testing ? (
                  <>
                    <Loader2 size={16} className="spin" />
                    Testing Ping...
                  </>
                ) : (
                  <>
                    <Zap size={16} />
                    Test Connection
                  </>
                )}
              </button>

              <div style={{ display: "flex", gap: 10 }}>
                <button type="button" className="btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save Settings
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

