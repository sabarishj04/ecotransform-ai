/**
 * EcoTransform AI - Client Application Logic
 * Manages UI tabs, webcam WebRTC, drag-and-drop, API requests,
 * Waste-to-Wealth cards, and dynamic sustainability charts.
 */

// ================= STATE MANAGEMENT =================
const state = {
  currentTab: 'landing',
  sessionId: getOrCreateSessionId(),
  selectedFile: null,
  selectedBase64: null,
  currentScanData: null,
  historyData: [],
  dashboardChart: null,
  cameraStream: null
};

function getOrCreateSessionId() {
  let sid = localStorage.getItem('ecotransform_session_id');
  if (!sid) {
    sid = 'session_' + Math.random().toString(36).substring(2, 15) + '_' + Date.now();
    localStorage.setItem('ecotransform_session_id', sid);
  }
  return sid;
}

// ================= TAB NAVIGATION =================
function switchTab(tabId) {
  state.currentTab = tabId;

  // Toggle tab contents
  document.querySelectorAll('.tab-content').forEach(section => {
    section.classList.add('hidden');
  });

  const activeSection = document.getElementById(`view-${tabId}`);
  if (activeSection) {
    activeSection.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Update nav buttons
  document.querySelectorAll('.nav-btn').forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('bg-eco-100', 'text-eco-800', 'font-bold');
      btn.classList.remove('text-slate-700');
    } else {
      btn.classList.remove('bg-eco-100', 'text-eco-800', 'font-bold');
      btn.classList.add('text-slate-700');
    }
  });

  // Re-initialize icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // Trigger data refreshes on view entrance
  if (tabId === 'dashboard') {
    fetchDashboardStats();
  } else if (tabId === 'history') {
    fetchHistory();
  }
}

// ================= DRAG & DROP & PREVIEW =================
document.addEventListener('DOMContentLoaded', () => {
  const dropArea = document.getElementById('drop-area');
  const fileInput = document.getElementById('file-input');

  if (dropArea && fileInput) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropArea.classList.add('border-eco-500', 'bg-eco-50/50');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropArea.classList.remove('border-eco-500', 'bg-eco-50/50');
      }, false);
    });

    dropArea.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length) handleFile(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length) handleFile(e.target.files[0]);
    });
  }

  // Initialize Icons
  if (window.lucide) window.lucide.createIcons();
});

function handleFile(file) {
  if (!file.type.startsWith('image/')) {
    alert('Please select a valid image file (JPEG, PNG, WEBP).');
    return;
  }
  if (file.size > 6 * 1024 * 1024) {
    alert('Image file exceeds the 6MB limit. Please choose a smaller image.');
    return;
  }

  state.selectedFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    state.selectedBase64 = e.target.result;
    renderImagePreview(e.target.result);
  };
  reader.readAsDataURL(file);
}

function renderImagePreview(src) {
  const placeholder = document.getElementById('upload-placeholder');
  const container = document.getElementById('preview-container');
  const img = document.getElementById('preview-image');
  const btn = document.getElementById('btn-analyze');

  img.src = src;
  placeholder.classList.add('hidden');
  container.classList.remove('hidden');
  btn.disabled = false;
  btn.classList.remove('opacity-40', 'cursor-not-allowed');
}

// ================= WEBRTC CAMERA =================
async function openCameraModal() {
  const modal = document.getElementById('camera-modal');
  const video = document.getElementById('camera-feed');
  modal.classList.remove('hidden');

  try {
    state.cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1280 } },
      audio: false
    });
    video.srcObject = state.cameraStream;
  } catch (err) {
    console.warn('Camera access denied or unavailable:', err);
    alert('Unable to access device camera. Please upload an image file instead.');
    closeCameraModal();
  }
}

function closeCameraModal() {
  const modal = document.getElementById('camera-modal');
  modal.classList.add('hidden');
  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach(track => track.stop());
    state.cameraStream = null;
  }
}

function captureCameraSnapshot() {
  const video = document.getElementById('camera-feed');
  if (!video) return;

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
  state.selectedBase64 = dataUrl;
  state.selectedFile = null;

  renderImagePreview(dataUrl);
  closeCameraModal();
}

// ================= AI ANALYSIS PIPELINE =================
async function submitAnalysis() {
  if (!state.selectedFile && !state.selectedBase64) return;

  const btn = document.getElementById('btn-analyze');
  const btnText = document.getElementById('btn-analyze-text');
  const laser = document.getElementById('scanner-laser');
  const loading = document.getElementById('scan-loading');

  // UI state: Loading with laser scanner
  btn.disabled = true;
  btnText.textContent = 'Analyzing Material...';
  laser.classList.remove('hidden');
  loading.classList.remove('hidden');

  try {
    let response;
    if (state.selectedFile) {
      const formData = new FormData();
      formData.append('image', state.selectedFile);
      formData.append('session_id', state.sessionId);

      response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'X-Session-ID': state.sessionId },
        body: formData
      });
    } else {
      response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': state.sessionId
        },
        body: JSON.stringify({
          image_b64: state.selectedBase64,
          filename: 'camera_capture.jpg'
        })
      });
    }

    if (!response.ok) {
      throw new Error(`Server returned error ${response.status}`);
    }

    const scanData = await response.json();
    state.currentScanData = scanData;

    // Trigger celebration confetti
    if (window.confetti) {
      window.confetti({ particleCount: 70, spread: 60, origin: { y: 0.6 } });
    }

    renderScanResults(scanData, state.selectedBase64);
    switchTab('results');

  } catch (err) {
    console.error('Scan error:', err);
    alert('Analysis failed. Please check your image or try one of the instant demo presets.');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Analyze Waste Material';
    laser.classList.add('hidden');
    loading.classList.add('hidden');
  }
}

// ================= RENDER RESULTS VIEW =================
function renderScanResults(data, imageSrc) {
  const analysis = data.waste_analysis || {};
  const impact = data.environmental_impact || {};
  const recs = data.upcycle_recommendations || [];

  // Top header & image
  document.getElementById('res-item-name').textContent = analysis.item_name || 'Analyzed Waste Item';
  document.getElementById('res-material').textContent = analysis.primary_material || 'Composite';
  document.getElementById('res-condition').textContent = analysis.physical_condition || 'Used';
  document.getElementById('res-image-preview').src = imageSrc || data.image_preview || '';
  
  const scorePercent = Math.round((analysis.confidence_score || 0.90) * 100);
  document.getElementById('res-confidence-badge').textContent = `${scorePercent}% AI Match`;

  // Reasoning & Disposal
  document.getElementById('res-reasoning').textContent = analysis.identification_reasoning || 'Evaluated via visual geometry and composition markers.';
  document.getElementById('res-disposal').textContent = analysis.disposal_recommendation || 'Follow local municipal sorting guidelines.';

  // Categories Stream Badges
  const catContainer = document.getElementById('res-categories-container');
  catContainer.innerHTML = '';
  const categories = analysis.categories || ['Recyclable'];
  
  categories.forEach(cat => {
    const badge = document.createElement('span');
    badge.className = 'px-3 py-1 rounded-full text-xs font-bold ';
    if (cat.toLowerCase().includes('hazard')) {
      badge.className += 'bg-rose-100 text-rose-800 border border-rose-300';
    } else if (cat.toLowerCase().includes('recycl')) {
      badge.className += 'bg-emerald-100 text-emerald-800 border border-emerald-300';
    } else if (cat.toLowerCase().includes('reus')) {
      badge.className += 'bg-sky-100 text-sky-800 border border-sky-300';
    } else if (cat.toLowerCase().includes('bio')) {
      badge.className += 'bg-amber-100 text-amber-800 border border-amber-300';
    } else {
      badge.className += 'bg-slate-100 text-slate-800 border border-slate-300';
    }
    badge.textContent = cat;
    catContainer.appendChild(badge);
  });

  // Environmental Metrics
  document.getElementById('res-impact-co2').textContent = `${impact.co2_avoided_kg || 0.05} kg`;
  document.getElementById('res-impact-landfill').textContent = `${impact.landfill_diverted_kg || 0.02} kg`;
  document.getElementById('res-impact-water').textContent = `${impact.water_saved_liters || 0.3} L`;

  // Render 3 Waste-to-Wealth Recommendations
  const recGrid = document.getElementById('res-recommendations-grid');
  recGrid.innerHTML = '';

  recs.forEach((rec, idx) => {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between';

    // Difficulty styling
    const diff = (rec.difficulty || 'Easy').toLowerCase();
    let diffColor = 'bg-emerald-100 text-emerald-800';
    if (diff === 'medium') diffColor = 'bg-amber-100 text-amber-800';
    if (diff === 'hard') diffColor = 'bg-indigo-100 text-indigo-800';

    const profit = Math.max(0, (rec.potential_value_usd || 5) - (rec.estimated_cost_usd || 0)).toFixed(2);

    card.innerHTML = `
      <div>
        <!-- Card Header Badges -->
        <div class="flex items-center justify-between gap-2 mb-3">
          <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold ${diffColor}">
            ${rec.difficulty || 'Easy'} • ${rec.estimated_time_mins || 15} mins
          </span>
          <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-amber-50 text-amber-700 border border-amber-200">
            +$${profit} Est. ROI
          </span>
        </div>

        <h4 class="font-bold text-lg text-slate-900 leading-snug">${rec.product_name || 'Upcycled Blueprint'}</h4>

        <!-- Value vs Cost Breakdown -->
        <div class="mt-3 p-3 bg-slate-50 rounded-xl flex items-center justify-between text-xs">
          <div>
            <span class="text-slate-600 block">Est. Cost:</span>
            <span class="font-bold text-slate-800">$${(rec.estimated_cost_usd || 0).toFixed(2)}</span>
          </div>
          <div class="text-right">
            <span class="text-slate-600 block">Market Value:</span>
            <span class="font-extrabold text-emerald-600">$${(rec.potential_value_usd || 5).toFixed(2)}</span>
          </div>
        </div>

        <!-- Materials & Tools -->
        <div class="mt-4 space-y-2 text-xs">
          <div>
            <strong class="text-slate-700">Materials:</strong>
            <span class="text-slate-600">${(rec.materials_needed || []).join(', ')}</span>
          </div>
          <div>
            <strong class="text-slate-700">Tools:</strong>
            <span class="text-slate-600">${(rec.tools_needed || []).join(', ')}</span>
          </div>
        </div>

        <!-- Step-by-Step Instructions -->
        <div class="mt-4 pt-3 border-t border-slate-100">
          <strong class="text-xs text-slate-800 block mb-2 font-bold flex items-center gap-1">
            <i data-lucide="list-ordered" class="w-3.5 h-3.5 text-eco-600"></i>
            <span>Step-by-Step Fabrication:</span>
          </strong>
          <ol class="text-xs text-slate-600 space-y-1.5 list-decimal pl-4">
            ${(rec.steps || []).map(step => `<li>${step}</li>`).join('')}
          </ol>
        </div>

        ${rec.safety_precautions && rec.safety_precautions.length ? `
          <div class="mt-3 p-2 bg-rose-50 border border-rose-200 rounded-lg text-[11px] text-rose-800">
            <strong>Safety Warning:</strong> ${rec.safety_precautions.join(' ')}
          </div>
        ` : ''}
      </div>

      <!-- Sustainability Footnote -->
      <div class="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-600 italic">
        🌿 ${rec.sustainability_benefit || 'Extends product lifespan and conserves natural resources.'}
      </div>
    `;

    recGrid.appendChild(card);
  });

  if (window.lucide) window.lucide.createIcons();
}

// ================= INSTANT DEMO PRESETS (HACKATHON WINNER) =================
function loadSamplePreset(type) {
  // SVG presets encoded directly as data-URIs
  const sampleDataMap = {
    plastic: {
      name: 'plastic_bottle.jpg',
      color: '#0284c7',
      svg: `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400"><rect width="400" height="400" fill="#e0f2fe"/><path d="M180,60 h40 v40 h-40 z M160,100 h80 v220 c0,15 -15,30 -40,30 c-25,0 -40,-15 -40,-30 z" fill="#38bdf8" stroke="#0284c7" stroke-width="4"/><text x="200" y="240" font-family="sans-serif" font-size="20" font-weight="bold" fill="#0369a1" text-anchor="middle">PET Bottle #1</text></svg>`
    },
    aluminum: {
      name: 'aluminum_can.jpg',
      color: '#e11d48',
      svg: `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400"><rect width="400" height="400" fill="#ffe4e6"/><rect x="150" y="80" width="100" height="240" rx="20" fill="#fb7185" stroke="#e11d48" stroke-width="4"/><ellipse cx="200" cy="80" rx="50" ry="15" fill="#f43f5e"/><text x="200" y="210" font-family="sans-serif" font-size="18" font-weight="bold" fill="#ffffff" text-anchor="middle">Soda Can 330ml</text></svg>`
    },
    cardboard: {
      name: 'cardboard_box.jpg',
      color: '#b45309',
      svg: `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400"><rect width="400" height="400" fill="#fef3c7"/><polygon points="120,160 200,120 280,160 200,200" fill="#d97706"/><polygon points="120,160 200,200 200,300 120,260" fill="#b45309"/><polygon points="200,200 280,160 280,260 200,300" fill="#92400e"/><text x="200" y="340" font-family="sans-serif" font-size="16" font-weight="bold" fill="#78350f" text-anchor="middle">Corrugated Box</text></svg>`
    },
    battery: {
      name: 'battery.jpg',
      color: '#dc2626',
      svg: `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400"><rect width="400" height="400" fill="#fee2e2"/><rect x="180" y="60" width="40" height="20" rx="3" fill="#9ca3af"/><rect x="150" y="80" width="100" height="240" rx="10" fill="#1f2937"/><rect x="150" y="80" width="100" height="70" fill="#f59e0b"/><text x="200" y="220" font-family="sans-serif" font-size="18" font-weight="bold" fill="#ef4444" text-anchor="middle">HAZARD</text><text x="200" y="250" font-family="sans-serif" font-size="12" fill="#9ca3af" text-anchor="middle">Li-ion Cell</text></svg>`
    }
  };

  const item = sampleDataMap[type] || sampleDataMap.plastic;
  const dataUrl = 'data:image/svg+xml;utf8,' + encodeURIComponent(item.svg);

  state.selectedBase64 = dataUrl;
  state.selectedFile = null;

  switchTab('scanner');
  renderImagePreview(dataUrl);

  // Trigger analysis immediately for lightning demo
  setTimeout(() => {
    submitAnalysis();
  }, 350);
}

// ================= DASHBOARD & CHARTS =================
async function fetchDashboardStats() {
  try {
    const res = await fetch(`/api/dashboard/stats?session_id=${state.sessionId}&scope=global`);
    if (!res.ok) return;
    const stats = await res.json();

    document.getElementById('dash-total-scans').textContent = stats.total_scans || 0;
    document.getElementById('dash-total-co2').textContent = `${(stats.total_co2_kg || 0).toFixed(2)} kg`;
    document.getElementById('dash-total-landfill').textContent = `${(stats.total_landfill_kg || 0).toFixed(2)} kg`;
    document.getElementById('dash-total-wealth').textContent = `$${(stats.total_wealth_potential_usd || 0).toFixed(2)}`;

    // Equivalency calculation
    const co2 = stats.total_co2_kg || 0;
    document.getElementById('equiv-trees').textContent = (co2 / 0.85).toFixed(1);
    document.getElementById('equiv-miles').textContent = (co2 * 2.5).toFixed(1);
    document.getElementById('equiv-led').textContent = Math.round(co2 * 120);

    renderMaterialDonutChart(stats.material_breakdown || []);
  } catch (err) {
    console.error('Dashboard fetch error:', err);
  }
}

function renderMaterialDonutChart(breakdown) {
  const canvas = document.getElementById('chart-material-donut');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (state.dashboardChart) {
    state.dashboardChart.destroy();
  }

  const labels = breakdown.length ? breakdown.map(b => b.material) : ['Plastic (PET)', 'Aluminum', 'Cardboard'];
  const counts = breakdown.length ? breakdown.map(b => b.count) : [3, 2, 1];

  state.dashboardChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: [
          '#10b981',
          '#38bdf8',
          '#f59e0b',
          '#f43f5e',
          '#8b5cf6',
          '#64748b'
        ],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' }
      },
      cutout: '65%'
    }
  });
}

// ================= SCAN HISTORY =================
async function fetchHistory() {
  try {
    const res = await fetch(`/api/history?session_id=${state.sessionId}`);
    if (!res.ok) return;
    const data = await res.json();
    state.historyData = data.scans || [];
    renderHistoryCards(state.historyData);
  } catch (err) {
    console.error('History fetch error:', err);
  }
}

function renderHistoryCards(scans) {
  const grid = document.getElementById('history-grid');
  const empty = document.getElementById('history-empty');

  if (!scans || scans.length === 0) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }

  empty.classList.add('hidden');
  grid.innerHTML = '';

  scans.forEach(scan => {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-2xl border border-slate-200 p-4 shadow-sm hover:shadow-md transition flex flex-col justify-between';

    const dateStr = new Date(scan.created_at).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });

    card.innerHTML = `
      <div>
        <div class="h-36 rounded-xl bg-slate-100 overflow-hidden flex items-center justify-center mb-3">
          ${scan.image_preview ? `<img src="${scan.image_preview}" class="h-full w-full object-cover">` : '<i data-lucide="image" class="w-8 h-8 text-slate-400"></i>'}
        </div>
        <div class="flex items-center justify-between gap-2 mb-1">
          <span class="text-[11px] font-bold text-slate-600">${dateStr}</span>
          <span class="text-[11px] font-bold text-eco-700 bg-eco-50 px-2 py-0.5 rounded-full">${Math.round(scan.confidence_score * 100)}% Match</span>
        </div>
        <h4 class="font-bold text-base text-slate-900">${scan.item_name}</h4>
        <p class="text-xs text-slate-600 mt-0.5">${scan.primary_material || 'Material'}</p>
      </div>

      <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
        <button onclick="loadPastScanDetail('${scan.id}')" class="text-xs font-bold text-eco-600 hover:text-eco-700 flex items-center gap-1">
          <span>View Recipes</span>
          <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
        </button>
        <button onclick="deleteScanRecord('${scan.id}')" class="p-1.5 text-slate-600 hover:text-rose-600 rounded-lg hover:bg-rose-50" title="Delete scan">
          <i data-lucide="trash" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    `;

    grid.appendChild(card);
  });

  if (window.lucide) window.lucide.createIcons();
}

function filterHistory() {
  const query = (document.getElementById('history-search').value || '').toLowerCase();
  const filtered = state.historyData.filter(s => 
    (s.item_name || '').toLowerCase().includes(query) ||
    (s.primary_material || '').toLowerCase().includes(query)
  );
  renderHistoryCards(filtered);
}

async function loadPastScanDetail(scanId) {
  try {
    const res = await fetch(`/api/history/${scanId}`);
    if (!res.ok) return;
    const scanData = await res.json();
    state.currentScanData = scanData;
    renderScanResults(scanData, scanData.image_preview);
    switchTab('results');
  } catch (err) {
    console.error('Error loading scan details:', err);
  }
}

async function deleteScanRecord(scanId) {
  if (!confirm('Are you sure you want to remove this scan from your history?')) return;
  try {
    const res = await fetch(`/api/history/${scanId}`, {
      method: 'DELETE',
      headers: { 'X-Session-ID': state.sessionId }
    });
    if (res.ok) {
      fetchHistory();
      fetchDashboardStats();
    }
  } catch (err) {
    console.error('Delete error:', err);
  }
}

function shareResult() {
  const itemName = document.getElementById('res-item-name').textContent;
  const co2 = document.getElementById('res-impact-co2').textContent;
  const text = `I just analyzed ${itemName} on EcoTransform AI and diverted waste saving ${co2} of CO₂! Check out your waste's value at EcoTransform.`;

  if (navigator.share) {
    navigator.share({ title: 'EcoTransform AI Impact', text: text, url: window.location.href });
  } else {
    navigator.clipboard.writeText(text);
    alert('Impact summary copied to clipboard! Share it with your team or social media.');
  }
}
