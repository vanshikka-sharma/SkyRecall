import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../api';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handle = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.username || !form.password) return toast.error('All fields required');
    setLoading(true);
    try {
      const { data } = await api.post('/auth/login/', form);

      // Store tokens and user properly
      login(data.user, data.tokens);
      
      toast.success(data.message);
      navigate('/dashboard');
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.response?.data?.non_field_errors?.[0] || 'Login failed';
      toast.error(errorMsg);
    } finally { setLoading(false); }
  };

  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div className="hero-logo">Sky<span>Recall</span></div>
        <p className="hero-tagline">Your memories, intelligently recalled.</p>
        <div className="hero-features">
          {[
            ['🧠', 'AI-powered semantic search'],
            ['📸', 'Upload hundreds of photos'],
            ['🔍', 'Search in plain English'],
            ['⚡', 'Instant results with CLIP'],
          ].map(([icon, text]) => (
            <div className="hero-feature" key={text}>
              <div className="hero-feature-icon">{icon}</div>
              {text}
            </div>
          ))}
        </div>
      </div>
      <div className="auth-form-container">
        <div className="auth-form-box">
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtitle">Sign in to access your photo memories</p>
          <form onSubmit={submit}>
            <div className="form-group">
              <label>Username</label>
              <input className="form-input" name="username" value={form.username} onChange={handle} placeholder="your_username" autoComplete="username" />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input className="form-input" name="password" type="password" value={form.password} onChange={handle} placeholder="••••••••" autoComplete="current-password" />
            </div>
            <button className="btn-primary" type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In →'}
            </button>
          </form>
          <p className="auth-switch">Don't have an account? <Link to="/register">Create one</Link></p>
        </div>
      </div>
    </div>
  );
}