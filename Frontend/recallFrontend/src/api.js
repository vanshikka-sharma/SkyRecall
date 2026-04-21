import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/",
});

// 🔥 THIS IS THE FIX
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");

  console.log("TOKEN SENT:", token); 

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export default api;