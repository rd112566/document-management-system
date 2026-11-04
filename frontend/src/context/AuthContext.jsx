import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../services/api";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("dms_token") || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem("dms_user");
    if (savedUser && token) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem("dms_user");
        setUser(null);
      }
    } else {
      setUser(null);
    }
    setLoading(false);

    const handleAuthLogout = () => {
      setToken(null);
      setUser(null);
    };

    window.addEventListener("auth_logout", handleAuthLogout);
    return () => window.removeEventListener("auth_logout", handleAuthLogout);
  }, [token]);

  const login = async (username, password) => {
    const res = await api.post("/api/auth/login", { username, password });
    const { access_token, user: loggedUser } = res.data;
    localStorage.setItem("dms_token", access_token);
    localStorage.setItem("dms_user", JSON.stringify(loggedUser));
    setToken(access_token);
    setUser(loggedUser);
    return res.data;
  };

  const signup = async (username, email, password) => {
    const res = await api.post("/api/auth/signup", { username, email, password });
    const { access_token, user: registeredUser } = res.data;
    localStorage.setItem("dms_token", access_token);
    localStorage.setItem("dms_user", JSON.stringify(registeredUser));
    setToken(access_token);
    setUser(registeredUser);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem("dms_token");
    localStorage.removeItem("dms_user");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, signup, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
