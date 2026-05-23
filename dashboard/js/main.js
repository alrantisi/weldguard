// ===== SHARED UTILITIES =====

// Clock
function startClock() {
  const el = document.getElementById('clock');
  const dateEl = document.getElementById('clock-date');
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    if (dateEl) {
      dateEl.textContent = now.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    }
  }
  tick();
  setInterval(tick, 1000);
}

// Toast notifications
function showToast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const icons = {
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" color="var(--green)"><polyline points="20 6 9 17 4 12"/></svg>`,
    danger:  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" color="var(--red)"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" color="var(--yellow)"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `${icons[type] || ''}<span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateX(20px)'; toast.style.transition = 'all 0.25s'; setTimeout(() => toast.remove(), 260); }, 3200);
}

// Animated counter
function animateCounter(el, target, duration = 1200, prefix = '', suffix = '') {
  if (!el) return;
  let start = 0;
  const step = Math.ceil(duration / target) > 0 ? Math.ceil(duration / target) : 1;
  const timer = setInterval(() => {
    start += Math.max(1, Math.ceil(target / 60));
    if (start >= target) { start = target; clearInterval(timer); }
    el.textContent = prefix + start + suffix;
  }, 1000 / 60);
}

// Modal helpers
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('open');
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('open');
}

// Formatters
function fmtTime(date) {
  return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

const COLORS = {
  orange: '#f97316', green: '#22c55e', red: '#ef4444',
  blue: '#3b82f6', cyan: '#06b6d4', yellow: '#eab308', purple:'#a855f7',
  muted: '#4a5980'
};

// Mock worker data
const WORKERS = [
  { uid:'A1B2C3D4', name:'Ahmad Fauzi',    dept:'Las Struktural',  cert:'2026-08-10', status:'active',   avatar:'AF', color:'#f97316' },
  { uid:'E5F6G7H8', name:'Bambang Setyo',  dept:'Las Pipa',        cert:'2025-12-20', status:'active',   avatar:'BS', color:'#3b82f6' },
  { uid:'I9J0K1L2', name:'Candra Wijaya',  dept:'Las Otomotif',    cert:'2026-03-15', status:'active',   avatar:'CW', color:'#22c55e' },
  { uid:'M3N4O5P6', name:'Dodi Hartono',   dept:'Las Struktural',  cert:'2025-06-01', status:'expired',  avatar:'DH', color:'#ef4444' },
  { uid:'Q7R8S9T0', name:'Eko Prasetyo',   dept:'Las Kapal',       cert:'2027-01-15', status:'active',   avatar:'EP', color:'#a855f7' },
  { uid:'U1V2W3X4', name:'Fajar Nugroho',  dept:'Las Pipa',        cert:'2026-11-30', status:'active',   avatar:'FN', color:'#06b6d4' },
  { uid:'Y5Z6A7B8', name:'Gilang Ramadan', dept:'Las Otomotif',    cert:'2025-09-18', status:'suspended',avatar:'GR', color:'#eab308' },
  { uid:'C9D0E1F2', name:'Hendra Kusuma',  dept:'Las Struktural',  cert:'2026-06-22', status:'active',   avatar:'HK', color:'#f97316' },
];

// Backend API Base URL
const API_BASE_URL = 'http://127.0.0.1:8000/api';

// Global Data
let STATIONS = [];
let INCIDENTS = [];

// Fetch data dari backend
async function fetchLiveData() {
  try {
    // Ambil status stasiun
    const resStatus = await fetch(`${API_BASE_URL}/status`);
    if (resStatus.ok) {
      const dataStatus = await resStatus.json();
      const stationDict = dataStatus.data || {};
      
      // Convert dict to array
      STATIONS = Object.keys(stationDict).map(id => {
        const s = stationDict[id];
        return {
          id: id,
          name: s.name,
          worker: s.worker,
          uid: s.uid,
          status: s.status,
          machine: s.machine,
          helm: s.apd_status?.welding_helmet ?? false,
          shield: s.apd_status?.face_shield ?? false,
          glasses: s.apd_status?.safety_glasses ?? false
        };
      });
    }

    // Ambil log insiden
    const resIncidents = await fetch(`${API_BASE_URL}/incidents`);
    if (resIncidents.ok) {
      const dataIncidents = await resIncidents.json();
      INCIDENTS = dataIncidents.data || [];
    }

  } catch (error) {
    console.error("Gagal mengambil data dari backend:", error);
  }
}

// Start polling
function startDataPolling(onUpdate, interval = 2000) {
  fetchLiveData().then(onUpdate);
  setInterval(async () => {
    await fetchLiveData();
    if (onUpdate) onUpdate();
  }, interval);
}

// Init on DOM load
document.addEventListener('DOMContentLoaded', () => {
  startClock();
  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });
  // Close modal buttons
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-close-modal');
      closeModal(id);
    });
  });
});
