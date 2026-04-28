import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import api from '../api';
import { useAuth } from '../context/AuthContext';

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  // Handle logout with token blacklist
  const handleLogout = async () => {
    try {
      await api.post('/auth/logout/', {
        refresh: localStorage.getItem("refresh")
      });
    } catch (err) {
      // Ignore logout errors - just clear local storage
    }
    logout();
    navigate('/login');
  };
  const [tab, setTab] = useState('gallery');
  const [photos, setPhotos] = useState([]);
  const [results, setResults] = useState(null);
  const [query, setQuery] = useState('');
  const [stats, setStats] = useState({ total_photos: 0, indexed_photos: 0 });
  const [uploading, setUploading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [lightbox, setLightbox] = useState(null);
  const [uploadQueue, setUploadQueue] = useState([]);

  const loadPhotos = async () => {
    try {
      const { data } = await api.get('/photos/');
      setPhotos(data.photos);
    } catch { toast.error('Failed to load photos'); }
  };

  const loadStats = async () => {
    try {
      const { data } = await api.get('/stats/');
      setStats(data);
    } catch {}
  };

  useEffect(() => { loadPhotos(); loadStats(); }, []);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!acceptedFiles.length) return;
    setUploadQueue(acceptedFiles.map(f => ({ name: f.name, progress: 0, done: false })));
    setUploading(true);
    setTab('upload');

    const formData = new FormData();
    acceptedFiles.forEach(f => formData.append('images', f));

    try {
      setUploadQueue(q => q.map(i => ({ ...i, progress: 50 })));
      const { data } = await api.post('/photos/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          const pct = Math.round((e.loaded / e.total) * 80);
          setUploadQueue(q => q.map(i => ({ ...i, progress: pct })));
        }
      });
      setUploadQueue(q => q.map(i => ({ ...i, progress: 100, done: true })));
      toast.success(data.message);
      await loadPhotos();
      await loadStats();
      if (data.errors?.length) data.errors.forEach(e => toast.error(e));
    } catch (err) {
      toast.error(err.response?.data?.error || 'Upload failed');
    } finally { setUploading(false); }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'image/*': [] }, multiple: true
  });

  const search = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return toast.error('Type something to search');
    setSearching(true);
    setResults(null);
    try {
      const { data } = await api.get(`/search/?q=${encodeURIComponent(query)}`);
      setResults(data);
      setTab('results');
      if (data.count === 0) toast('No matching photos found', { icon: '🔍' });
    } catch (err) {
      toast.error(err.response?.data?.error || 'Search failed');
    } finally { setSearching(false); }
  };

  const deletePhoto = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this photo?')) return;
    try {
      await api.delete(`/photos/${id}/`);
      setPhotos(p => p.filter(x => x.id !== id));
      if (results) setResults(r => ({ ...r, results: r.results.filter(x => x.id !== id) }));
      await loadStats();
      toast.success('Photo deleted');
    } catch { toast.error('Delete failed'); }
  };

  const initials = user ? (user.first_name?.[0] || user.username?.[0] || 'U').toUpperCase() : 'U';
  const displayName = user?.first_name || user?.username || 'User';

  const PhotoGrid = ({ items, showScore }) => (
    items.length ? (
      <div className="photo-grid">
        {items.map(photo => (
          <div className="photo-card" key={photo.id} onClick={() => setLightbox(photo)}>
            <button className="photo-delete-btn" onClick={(e) => deletePhoto(photo.id, e)}>✕</button>
            {showScore && photo.score !== undefined && photo.score !== null && (
              <div className="photo-card-score">
                {Math.round(photo.score * 100)}%
              </div>
            )}
            <img src={photo.image_url} alt={photo.title} loading="lazy" />
            <div className="photo-card-body">
              <div className="photo-card-name">{photo.title || 'Untitled'}</div>
            </div>
          </div>
        ))}
      </div>
    ) : (
      <div className="empty-state">
        <div className="empty-icon">📭</div>
        <div className="empty-title">No photos here</div>
        <div className="empty-hint">Upload some photos to get started!</div>
      </div>
    )
  );

  return (
    <div className="dashboard">
      <div className="topbar">
        <div className="topbar-logo">Sky<span>Recall</span></div>
        <div className="topbar-right">
          <div className="user-pill">
            <div className="user-avatar">{initials}</div>
            {displayName}
          </div>
          <button className="btn-logout" onClick={handleLogout}>Sign out</button>
        </div>
      </div>

      <div className="dashboard-body">
        {/* Stats */}
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-number">{stats.total_photos}</div>
            <div className="stat-label">Total Photos</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{stats.indexed_photos}</div>
            <div className="stat-label">AI Indexed</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{stats.pending_indexing || 0}</div>
            <div className="stat-label">Pending</div>
          </div>
        </div>

        {/* Search bar */}
        <div className="search-section">
          <h2 className="search-label">Search your <span>memories</span></h2>
          <form className="search-bar-wrap" onSubmit={search}>
            <input
              className="search-input"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder='Try "sunset on a beach", "birthday cake", "my cat"...'
            />
            <button className="search-btn" type="submit" disabled={searching}>
              {searching ? '⏳' : '🔍'}
            </button>
          </form>
        </div>

        {/* Tabs */}
        <div className="tabs">
          <button className={`tab-btn ${tab === 'gallery' ? 'active' : ''}`} onClick={() => setTab('gallery')}>
            📸 My Photos ({photos.length})
          </button>
          <button className={`tab-btn ${tab === 'upload' ? 'active' : ''}`} onClick={() => setTab('upload')}>
            ⬆️ Upload
          </button>
          {results && (
            <button className={`tab-btn ${tab === 'results' ? 'active' : ''}`} onClick={() => setTab('results')}>
              🎯 Results ({results.count})
            </button>
          )}
        </div>

        {/* Tab: Gallery */}
        {tab === 'gallery' && <PhotoGrid items={photos} showScore={false} />}

        {/* Tab: Upload */}
        {tab === 'upload' && (
          <div>
            <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'active' : ''}`}>
              <input {...getInputProps()} />
              <div className="upload-icon">🖼️</div>
              <div className="upload-title">{isDragActive ? 'Drop your photos here!' : 'Drag & drop photos'}</div>
              <p className="upload-hint">or click to browse — JPG, PNG, WEBP supported (up to 50 images)</p>
              <button className="upload-btn" type="button" onClick={e => e.stopPropagation()}>Browse Files</button>
            </div>

            {uploadQueue.length > 0 && (
              <div className="upload-progress">
                {uploadQueue.map((item, i) => (
                  <div className="progress-item" key={i}>
                    <span className="progress-name">{item.name}</span>
                    <div className="progress-bar-wrap">
                      <div className="progress-bar" style={{ width: `${item.progress}%` }} />
                    </div>
                    <span className="progress-status">{item.done ? '✓ Done' : `${item.progress}%`}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab: Results */}
        {tab === 'results' && results && (
          <div>
            <p style={{ color: 'var(--muted)', marginBottom: '20px', fontSize: '0.9rem' }}>
              Found <strong style={{ color: 'var(--text)' }}>{results.count}</strong> result{results.count !== 1 ? 's' : ''} for "<em style={{ color: 'var(--accent)' }}>{results.query}</em>"
            </p>
            {results.count === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🔍</div>
                <div className="empty-title">No matches found</div>
                <div className="empty-hint">Try different keywords — "person smiling", "red car", "mountain landscape"</div>
              </div>
            ) : (
              <PhotoGrid items={results.results} showScore={true} />
            )}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div className="lightbox-overlay" onClick={() => setLightbox(null)}>
          <button className="lightbox-close" onClick={() => setLightbox(null)}>✕</button>
          <img className="lightbox-img" src={lightbox.image_url} alt={lightbox.title} onClick={e => e.stopPropagation()} />
        </div>
      )}
    </div>
  );
}