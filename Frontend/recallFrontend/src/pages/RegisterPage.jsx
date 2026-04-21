import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../api';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const [form, setForm] = useState({ first_name: '', last_name: '', username: '', email: '', password: '', password2: '' });
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handle = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  // const submit = async (e) => {
  //   e.preventDefault();
  //   if (form.password !== form.password2) return toast.error('Passwords do not match');
  //   setLoading(true);
  //   try {
  //     const { data } = await api.post('/auth/register/', form);
  //     console.log("SUCCESS RESPONSE:", res.data);  ////
  //     login(data.user, data.tokens);
  //     toast.success('Account created! Welcome to SkyRecall 🎉');
  //     navigate('/dashboard');
  //   } catch (err) {
  //     console.log("FULL ERROR RESPONSE:", err.response?.data);   ////
  //     console.log("FULL ERROR:", err);
  //     const errs = err.response?.data;
  //     if (errs) {
  //       Object.values(errs).forEach(msgs => msgs.forEach?.(m => toast.error(m)));
  //     } else {
  //       toast.error('Registration failed');
  //     }
  //   } finally { setLoading(false); }
  // };

  const submit = async (e) => {
    e.preventDefault();

    if (form.password !== form.password2)
      return toast.error('Passwords do not match');

    setLoading(true);

    try {
      const res = await api.post('/auth/register/', form);

      console.log("SUCCESS:", res.data); // ✅ correct

      login(res.data.user, res.data.tokens);

      toast.success('Account created!');
      navigate('/dashboard');

    } catch (err) {
      console.log("ERROR:", err.response?.data);
      console.log("NETWORK ERROR:", err);

      toast.error('Registration failed');
    } finally {
      setLoading(false);
    }
    console.log("FINAL FORM:", form);   ////////
  };

  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div className="hero-logo">Sky<span>Recall</span></div>
        <p className="hero-tagline">Start searching your memories with AI.</p>
        <div className="hero-features">
          {[
            ['🔒', 'Secure private storage'],
            ['🧠', 'CLIP AI model (OpenAI)'],
            ['🌍', 'Search in any language'],
            ['🚀', 'College-grade ML project'],
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
          <h1 className="auth-title">Create account</h1>
          <p className="auth-subtitle">Join SkyRecall and search your memories</p>
          <form onSubmit={submit}>
            <div className="form-row">
              <div className="form-group"><label>First Name</label><input className="form-input" name="first_name" value={form.first_name} onChange={handle} placeholder="John" /></div>
              <div className="form-group"><label>Last Name</label><input className="form-input" name="last_name" value={form.last_name} onChange={handle} placeholder="Doe" /></div>
            </div>
            <div className="form-group"><label>Username</label><input className="form-input" name="username" value={form.username} onChange={handle} placeholder="johndoe123" /></div>
            <div className="form-group"><label>Email</label><input className="form-input" name="email" type="email" value={form.email} onChange={handle} placeholder="john@example.com" /></div>
            <div className="form-row">
              <div className="form-group"><label>Password</label><input className="form-input" name="password" type="password" value={form.password} onChange={handle} placeholder="••••••••" /></div>
              <div className="form-group"><label>Confirm</label><input className="form-input" name="password2" type="password" value={form.password2} onChange={handle} placeholder="••••••••" /></div>
            </div>
            <button className="btn-primary" type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Account →'}
            </button>
          </form>
          <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
        </div>
      </div>
    </div>
  );
}