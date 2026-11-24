/**
 * EcoTransform AI - Client Application Logic
 * Manages UI tabs, webcam WebRTC, drag-and-drop, API requests,
 * Waste-to-Wealth cards, and dynamic sustainability charts.
 */

// ================= STATE MANAGEMENT =================
const state = {
  currentTab: 'landing',
  sessionId: getOrCreateSessionId(),
  scannerMode: 'upload', // 'camera' | 'upload' | 'barcode' | 'text' | 'manual'
  selectedFile: null,
  selectedBase64: null,
  scannedBarcode: '',
  verifiedProductData: null,
  manualCorrection: null,
  textDescription: '',
  manualCategory: '',
  manualCondition: 'Clean & Intact',
  manualItemDetails: '',
  clarificationData: null,
  clarificationAnswer: '',
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

// ================= BARCODE & QR RECOGNITION WORKFLOW =================
function setBarcodeSample(sampleCode) {
  const input = document.getElementById('barcode-input-field');
  if (input) {
    input.value = sampleCode;
    state.scannedBarcode = sampleCode;
    lookupScannedBarcode();
  }
}

function onBarcodeInputChanged() {
  const val = (document.getElementById('barcode-input-field')?.value || '').trim();
  state.scannedBarcode = val;
  validateScannerForm();
}

function clearBarcodeInput() {
  const input = document.getElementById('barcode-input-field');
  if (input) input.value = '';
  state.scannedBarcode = '';
  state.verifiedProductData = null;
  state.manualCorrection = null;
  
  const mCard = document.getElementById('barcode-match-card');
  const uCard = document.getElementById('barcode-unmatched-card');
  if (mCard) mCard.classList.add('hidden');
  if (uCard) uCard.classList.add('hidden');
  
  validateScannerForm();
}

async function lookupScannedBarcode() {
  const barcode = (document.getElementById('barcode-input-field')?.value || state.scannedBarcode || '').trim();
  if (!barcode) {
    showScannerError('Please enter a barcode number or scan a QR code first.');
    return;
  }

  hideScannerError();
  const mCard = document.getElementById('barcode-match-card');
  const uCard = document.getElementById('barcode-unmatched-card');

  try {
    const res = await fetch('/api/barcode/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ barcode: barcode })
    });

    const data = await res.json();
    state.scannedBarcode = barcode;

    if (data.found && data.verified) {
      state.verifiedProductData = data;
      state.manualCorrection = null;

      // Populate Match Card
      document.getElementById('barcode-match-product').textContent = data.product_name;
      document.getElementById('barcode-match-manufacturer').textContent = data.manufacturer || data.brand_owner || 'Verified Brand';
      document.getElementById('barcode-type-badge').textContent = data.barcode_type || 'UPC / EAN';
      document.getElementById('barcode-match-material').textContent = data.packaging?.primary_material || 'Recyclable Polymer';
      document.getElementById('barcode-match-source').textContent = data.source || 'Verified Packaging Ledger';

      if (mCard) mCard.classList.remove('hidden');
      if (uCard) uCard.classList.add('hidden');

      showActivePreviewBadge('', `Barcode: ${barcode}`, data.product_name);
    } else {
      state.verifiedProductData = null;
      if (mCard) mCard.classList.add('hidden');
      if (uCard) {
        document.getElementById('barcode-unmatched-msg').textContent = data.message || `No verified match found for code '${barcode}'. You can specify the product details manually.`;
        uCard.classList.remove('hidden');
      }
    }
    validateScannerForm();
  } catch (err) {
    console.error('Barcode lookup error:', err);
    showScannerError('Unable to connect to barcode registry. You can specify product details manually.');
  }
}

// Manual Product Correction Dialog
function openManualCorrectionModal() {
  const modal = document.getElementById('manual-correction-modal');
  if (!modal) return;
  
  const nameInput = document.getElementById('corr-product-name');
  if (nameInput) {
    nameInput.value = state.verifiedProductData?.product_name || (state.scannedBarcode ? `Product #${state.scannedBarcode}` : '');
  }
  modal.classList.remove('hidden');
  if (window.lucide) window.lucide.createIcons();
}

function closeManualCorrectionModal() {
  const modal = document.getElementById('manual-correction-modal');
  if (modal) modal.classList.add('hidden');
}

function saveManualCorrection() {
  const nameVal = (document.getElementById('corr-product-name')?.value || '').trim();
  const matVal = document.getElementById('corr-material-select')?.value || 'Polyethylene Terephthalate (PET, #1)';
  const notesVal = (document.getElementById('corr-notes')?.value || '').trim();

  if (!nameVal) {
    alert('Please enter a product name.');
    return;
  }

  state.manualCorrection = {
    product_name: nameVal,
    material: matVal,
    notes: notesVal
  };

  closeManualCorrectionModal();

  // Update UI Card
  const mCard = document.getElementById('barcode-match-card');
  const uCard = document.getElementById('barcode-unmatched-card');
  if (mCard) {
    document.getElementById('barcode-match-badge').textContent = 'USER SPECIFIED';
    document.getElementById('barcode-match-badge').className = 'px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-indigo-100 text-indigo-800 border border-indigo-200';
    document.getElementById('barcode-match-product').textContent = nameVal;
    document.getElementById('barcode-match-manufacturer').textContent = notesVal || 'User Defined';
    document.getElementById('barcode-match-material').textContent = matVal;
    document.getElementById('barcode-match-source').textContent = 'User Manual Correction';
    mCard.classList.remove('hidden');
  }
  if (uCard) uCard.classList.add('hidden');

  showActivePreviewBadge('', `Linked: ${nameVal}`, matVal);
  validateScannerForm();
}

// ================= SCANNER 5-MODE SWITCHER =================
function setScannerMode(mode) {
  state.scannerMode = mode;

  // Toggle tab button active styles
  ['camera', 'upload', 'barcode', 'text', 'manual'].forEach(m => {
    const tabBtn = document.getElementById(`mode-tab-${m}`);
    const panel = document.getElementById(`method-panel-${m}`);
    if (tabBtn && panel) {
      if (m === mode) {
        tabBtn.classList.add('bg-white', 'text-eco-700', 'shadow-sm');
        tabBtn.classList.remove('text-slate-700');
        panel.classList.remove('hidden');
      } else {
        tabBtn.classList.remove('bg-white', 'text-eco-700', 'shadow-sm');
        tabBtn.classList.add('text-slate-700');
        panel.classList.add('hidden');
      }
    }
  });

  // If leaving camera tab, pause inline video stream to save battery
  if (mode !== 'camera' && state.cameraStream) {
    stopInlineCamera();
  }

  hideScannerError();
  validateScannerForm();

  if (window.lucide) window.lucide.createIcons();
}

function showScannerError(msg) {
  const box = document.getElementById('scanner-error-box');
  const text = document.getElementById('scanner-error-text');
  if (box && text) {
    text.textContent = msg;
    box.classList.remove('hidden');
  }
}

function hideScannerError() {
  const box = document.getElementById('scanner-error-box');
  if (box) box.classList.add('hidden');
}

function validateScannerForm() {
  const btn = document.getElementById('btn-analyze');
  if (!btn) return;

  let isValid = false;
  if (state.scannerMode === 'camera' || state.scannerMode === 'upload') {
    isValid = !!(state.selectedFile || state.selectedBase64);
  } else if (state.scannerMode === 'barcode') {
    isValid = !!(state.verifiedProductData || state.manualCorrection || (state.scannedBarcode && state.scannedBarcode.length >= 4));
  } else if (state.scannerMode === 'barcode') {
    const code = (document.getElementById('barcode-input-field')?.value || state.scannedBarcode || '').trim();
    if (!code) {
      showScannerError('Please enter a barcode number or select a verified test sample.');
      return;
    }
    payload = {
      input_method: 'barcode_scan',
      barcode: code,
      manual_correction: state.manualCorrection
    };
    if (loadHeader) loadHeader.textContent = 'Verifying Barcode / QR Registry...';
    if (loadSubtext) loadSubtext.textContent = 'Retrieving manufacturer packaging disclosure and lifecycle metrics...';

  } else if (state.scannerMode === 'text') {
    const textVal = (document.getElementById('text-waste-description')?.value || '').trim();
    isValid = textVal.length >= 3;
  } else if (state.scannerMode === 'manual') {
    const catVal = (document.getElementById('manual-material-select')?.value || '').trim();
    isValid = !!catVal;
  }

  btn.disabled = !isValid;
  if (isValid) {
    btn.classList.remove('opacity-40', 'cursor-not-allowed');
  } else {
    btn.classList.add('opacity-40', 'cursor-not-allowed');
  }
}
    const textVal = (document.getElementById('text-waste-description')?.value || '').trim();
    isValid = textVal.length >= 3;
  } else if (state.scannerMode === 'manual') {
    const catVal = (document.getElementById('manual-material-select')?.value || '').trim();
    isValid = !!catVal;
  }

  btn.disabled = !isValid;
  if (isValid) {
    btn.classList.remove('opacity-40', 'cursor-not-allowed');
  } else {
    btn.classList.add('opacity-40', 'cursor-not-allowed');
  }
}

// ================= INLINE CAMERA HANDLING =================
async function startInlineCamera() {
  const video = document.getElementById('live-camera-preview');
  const standby = document.getElementById('camera-standby-view');
  const controls = document.getElementById('camera-active-controls');
  const alertBox = document.getElementById('camera-permission-alert');
  const errorMsg = document.getElementById('camera-error-message');

  alertBox.classList.add('hidden');

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } },
      audio: false
    });
    state.cameraStream = stream;
    video.srcObject = stream;
    video.classList.remove('hidden');
    standby.classList.add('hidden');
    controls.classList.remove('hidden');
  } catch (err) {
    console.warn('Camera error:', err);
    let msg = 'Camera access was blocked or is unavailable. Please check your browser permissions.';
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      msg = 'Permission denied. Please grant camera permission in your browser URL bar.';
    } else if (err.name === 'NotFoundError') {
      msg = 'No video capture device found on your computer/phone.';
    }
    errorMsg.textContent = msg;
    alertBox.classList.remove('hidden');
    if (window.lucide) window.lucide.createIcons();
  }
}

function stopInlineCamera() {
  const video = document.getElementById('live-camera-preview');
  const standby = document.getElementById('camera-standby-view');
  const controls = document.getElementById('camera-active-controls');

  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach(t => t.stop());
    state.cameraStream = null;
  }
  if (video) {
    video.srcObject = null;
    video.classList.add('hidden');
  }
  if (standby) standby.classList.remove('hidden');
  if (controls) controls.classList.add('hidden');
}

function captureInlineSnapshot() {
  const video = document.getElementById('live-camera-preview');
  if (!video || !state.cameraStream) return;

  const canvas = document.getElementById('camera-capture-canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
  state.selectedBase64 = dataUrl;
  state.selectedFile = null;

  stopInlineCamera();
  showActivePreviewBadge(dataUrl, 'Live Camera Snapshot', 'Captured from device sensor');
  validateScannerForm();
}

// ================= TEXT DESCRIPTION HELPERS =================
function setTextExample(exampleText) {
  const textarea = document.getElementById('text-waste-description');
  if (textarea) {
    textarea.value = exampleText;
    textarea.focus();
    validateScannerForm();
  }
}

// ================= MANUAL CATEGORY HELPERS =================
function onManualCategoryChanged() {
  validateScannerForm();
}

// ================= PREVIEW BADGE & CLEAR =================
function showActivePreviewBadge(imgSrc, title, subtitle) {
  const badge = document.getElementById('active-item-preview-badge');
  const thumb = document.getElementById('badge-thumbnail');
  const bTitle = document.getElementById('badge-title');
  const bSub = document.getElementById('badge-subtitle');

  if (badge && thumb) {
    thumb.src = imgSrc;
    bTitle.textContent = title;
    bSub.textContent = subtitle;
    badge.classList.remove('hidden');
  }

  // Also update upload preview container if in upload mode
  const uploadImg = document.getElementById('preview-image');
  const uploadContainer = document.getElementById('preview-container');
  const uploadPlaceholder = document.getElementById('upload-placeholder');
  if (uploadImg && uploadContainer && uploadPlaceholder) {
    uploadImg.src = imgSrc;
    uploadPlaceholder.classList.add('hidden');
    uploadContainer.classList.remove('hidden');
  }

  if (window.lucide) window.lucide.createIcons();
}

function clearCurrentInput() {
  state.selectedFile = null;
  state.selectedBase64 = null;
  stopInlineCamera();

  // Reset file input
  const fileInput = document.getElementById('file-input');
  if (fileInput) fileInput.value = '';

  // Reset upload area
  const placeholder = document.getElementById('upload-placeholder');
  const container = document.getElementById('preview-container');
  const img = document.getElementById('preview-image');
  if (img) img.src = '';
  if (placeholder) placeholder.classList.remove('hidden');
  if (container) container.classList.add('hidden');

  // Reset badge
  const badge = document.getElementById('active-item-preview-badge');
  if (badge) badge.classList.add('hidden');

  // Reset text
  const textarea = document.getElementById('text-waste-description');
  if (textarea) textarea.value = '';

  // Reset manual selects
  const catSelect = document.getElementById('manual-material-select');
  if (catSelect) catSelect.value = '';
  const itemDet = document.getElementById('manual-item-details');
  if (itemDet) itemDet.value = '';

  hideScannerError();
  validateScannerForm();
}

// ================= UNIFIED ANALYSIS WORKFLOW =================
async function submitUnifiedAnalysis(bypassClarification = false, clarificationAns = '') {
  hideScannerError();
  hideClarificationDialog();

  const btn = document.getElementById('btn-analyze');
  const btnText = document.getElementById('btn-analyze-text');
  const laser = document.getElementById('scanner-laser');
  const loading = document.getElementById('scan-loading');
  const loadHeader = document.getElementById('loading-header');
  const loadSubtext = document.getElementById('loading-subtext');

  let payload = {};
  let isMultipart = false;
  let formData = null;

  // Build payload based on active scanner mode
  if (state.scannerMode === 'camera') {
    if (!state.selectedBase64) {
      showScannerError('Please snap a photo using the camera before analyzing.');
      return;
    }
    payload = {
      input_method: 'camera',
      image_b64: state.selectedBase64,
      filename: 'camera_capture.jpg'
    };
    if (loadHeader) loadHeader.textContent = 'Analyzing Camera Snapshot...';
    if (loadSubtext) loadSubtext.textContent = 'Processing visual pixels and computing resin stream metrics...';

  } else if (state.scannerMode === 'upload') {
    if (state.selectedFile) {
      isMultipart = true;
      formData = new FormData();
      formData.append('image', state.selectedFile);
      formData.append('input_method', 'image_upload');
      formData.append('session_id', state.sessionId);
    } else if (state.selectedBase64) {
      payload = {
        input_method: 'image_upload',
        image_b64: state.selectedBase64,
        filename: 'upload.jpg'
      };
    } else {
      showScannerError('Please select or drag-and-drop a waste image file.');
      return;
    }
    if (loadHeader) loadHeader.textContent = 'Scanning Uploaded Image...';
    if (loadSubtext) loadSubtext.textContent = 'Analyzing material composition and generating 3 DIY blueprints...';

  } else if (state.scannerMode === 'barcode') {
    const code = (document.getElementById('barcode-input-field')?.value || state.scannedBarcode || '').trim();
    if (!code) {
      showScannerError('Please enter a barcode number or select a verified test sample.');
      return;
    }
    payload = {
      input_method: 'barcode_scan',
      barcode: code,
      manual_correction: state.manualCorrection
    };
    if (loadHeader) loadHeader.textContent = 'Verifying Barcode / QR Registry...';
    if (loadSubtext) loadSubtext.textContent = 'Retrieving manufacturer packaging disclosure and lifecycle metrics...';

  } else if (state.scannerMode === 'text') {
    const textVal = (document.getElementById('text-waste-description')?.value || '').trim();
    if (textVal.length < 3) {
      showScannerError('Please provide a descriptive text note about your waste item (e.g. 500ml soda bottle).');
      return;
    }
    payload = {
      input_method: 'text_description',
      description: textVal,
      clarification_answer: clarificationAns || state.clarificationAnswer || '',
      bypass_clarification: bypassClarification
    };
    if (loadHeader) loadHeader.textContent = 'TEXT-BASED AI: Analyzing Description...';
    if (loadSubtext) loadSubtext.textContent = 'Evaluating likely material, color, texture, and recyclability stream...';

  } else if (state.scannerMode === 'manual') {
    const catVal = (document.getElementById('manual-material-select')?.value || '').trim();
    const condVal = (document.getElementById('manual-condition-select')?.value || 'Clean & Intact').trim();
    const detailVal = (document.getElementById('manual-item-details')?.value || '').trim();

    if (!catVal) {
      showScannerError('Please select a material category from the dropdown.');
      return;
    }

    payload = {
      input_method: 'manual_selection',
      material_category: catVal,
      item_details: detailVal ? `${detailVal} [Condition: ${condVal}]` : `Item in ${condVal} condition`
    };
    if (loadHeader) loadHeader.textContent = 'Configuring Category Blueprint...';
    if (loadSubtext) loadSubtext.textContent = `Structuring recycling pathway for ${catVal}...`;
  }

  // UI state: Loading with laser scanner
  btn.disabled = true;
  btnText.textContent = 'Analyzing...';
  if (laser) laser.classList.remove('hidden');
  if (loading) loading.classList.remove('hidden');

  try {
    let response;
    if (isMultipart) {
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
        body: JSON.stringify(payload)
      });
    }

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      throw new Error(errJson.message || `Server returned error ${response.status}`);
    }

    const data = await response.json();

    // Check if AI requested clarification before final analysis
    if (data.status === 'needs_clarification') {
      showClarificationDialog(data);
      return;
    }

    state.currentScanData = data;

    // Trigger celebration confetti
    if (window.confetti) {
      window.confetti({ particleCount: 70, spread: 60, origin: { y: 0.6 } });
    }

    const previewToDisplay = state.selectedBase64 || data.image_preview || '';
    renderScanResults(data, previewToDisplay);
    switchTab('results');

  } catch (err) {
    console.error('Scan error:', err);
    showScannerError(err.message || 'Analysis failed. Please try again or test with an instant preset.');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Analyze Waste Material';
    if (laser) laser.classList.add('hidden');
    if (loading) loading.classList.add('hidden');
    validateScannerForm();
  }
}

// Retain compatibility alias for preset buttons
function submitAnalysis() {
  submitUnifiedAnalysis();
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

  // Text description input listener for real-time validation
  const textarea = document.getElementById('text-waste-description');
  if (textarea) {
    textarea.addEventListener('input', () => {
      validateScannerForm();
    });
  }

  // Manual input details listener
  const manualDetails = document.getElementById('manual-item-details');
  if (manualDetails) {
    manualDetails.addEventListener('input', () => {
      validateScannerForm();
    });
  }

  // Default initial scanner validation
  validateScannerForm();

  // Initialize Icons
  if (window.lucide) window.lucide.createIcons();
});

function handleFile(file) {
  if (!file.type.startsWith('image/')) {
    showScannerError('Please select a valid image file (JPEG, PNG, WEBP, HEIC).');
    return;
  }
  if (file.size > 6 * 1024 * 1024) {
    showScannerError('Image file exceeds the 6MB limit. Please choose a smaller image.');
    return;
  }

  hideScannerError();
  state.selectedFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    state.selectedBase64 = e.target.result;
    renderImagePreview(e.target.result);
    showActivePreviewBadge(e.target.result, file.name, `${(file.size / 1024).toFixed(1)} KB image loaded`);
    validateScannerForm();
  };
  reader.readAsDataURL(file);
}

function renderImagePreview(src) {
  const placeholder = document.getElementById('upload-placeholder');
  const container = document.getElementById('preview-container');
  const img = document.getElementById('preview-image');

  if (img) img.src = src;
  if (placeholder) placeholder.classList.add('hidden');
  if (container) container.classList.remove('hidden');
  validateScannerForm();
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

  // Top header & method tag
  document.getElementById('res-item-name').textContent = analysis.item_name || 'Analyzed Waste Item';
  
  const methodTag = document.getElementById('res-method-tag');
  if (methodTag) {
    const methodStr = (data.identification_method || (data.input_method === 'text_description' ? 'TEXT-BASED AI' : 'MULTIMODAL VISION')).toUpperCase();
    methodTag.textContent = methodStr;
    if (methodStr.includes('TEXT')) {
      methodTag.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200';
    } else {
      methodTag.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-black uppercase tracking-wider bg-indigo-100 text-indigo-800 border border-indigo-200';
    }
  }

  // Material & Attributes
  document.getElementById('res-material').textContent = analysis.primary_material || 'Composite';
  document.getElementById('res-condition').textContent = analysis.physical_condition || 'Used';
  
  const colElem = document.getElementById('res-color');
  if (colElem) colElem.textContent = analysis.color || 'Standard';

  const texElem = document.getElementById('res-texture');
  if (texElem) texElem.textContent = analysis.texture || 'Standard';

  // Image Preview handling: If text-based, show an informative material SVG illustration
  const previewImg = document.getElementById('res-image-preview');
  if (imageSrc && imageSrc.length > 50) {
    previewImg.src = imageSrc;
  } else {
    // Generate an illustrative clean SVG placeholder for text-based analysis
    const matName = (analysis.primary_material || analysis.item_name || 'Waste').split(' ')[0];
    previewImg.src = 'data:image/svg+xml;utf8,' + encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
        <rect width="400" height="300" fill="#f0fdf4"/>
        <circle cx="200" cy="130" r="60" fill="#dcfce7" stroke="#16a34a" stroke-width="3"/>
        <text x="200" y="140" font-family="sans-serif" font-size="34" text-anchor="middle">🌱</text>
        <text x="200" y="225" font-family="sans-serif" font-size="16" font-weight="bold" fill="#15803d" text-anchor="middle">TEXT-BASED AI IDENTIFICATION</text>
        <text x="200" y="248" font-family="sans-serif" font-size="12" fill="#4b5563" text-anchor="middle">${matName} Stream Validated</text>
      </svg>
    `);
  }
  
  const scorePercent = Math.round((analysis.confidence_score || 0.92) * 100);
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

  // ================= POPULATE EVIDENCE FUSION SECTION =================
  const fusionCard = document.getElementById('fusion-section-card');
  const fusion = data.evidence_fusion;
  if (fusionCard && fusion) {
    fusionCard.classList.remove('hidden');

    // Count badge
    const countBadge = document.getElementById('fusion-sources-count');
    if (countBadge) {
      countBadge.textContent = `${fusion.source_count || 1} Source${(fusion.source_count || 1) > 1 ? 's' : ''}`;
    }

    // Basis text
    const basisText = document.getElementById('fusion-confidence-basis');
    if (basisText) {
      basisText.textContent = fusion.confidence_basis || 'Fused evidence across all available input streams.';
    }

    // Confidence badge styling (high, moderate, uncertain, conflicted)
    const confBadge = document.getElementById('fusion-confidence-badge');
    if (confBadge) {
      const lvl = (fusion.confidence_level || 'moderate').toLowerCase();
      confBadge.textContent = `${lvl.toUpperCase()} CONFIDENCE`;
      if (lvl === 'high') {
        confBadge.className = 'px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase bg-teal-500/20 text-teal-300 border border-teal-500/30';
      } else if (lvl === 'conflicted') {
        confBadge.className = 'px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse';
      } else if (lvl === 'uncertain') {
        confBadge.className = 'px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30';
      } else {
        confBadge.className = 'px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase bg-sky-500/20 text-sky-300 border border-sky-500/30';
      }
    }

    // Conflicts alert
    const conflictAlert = document.getElementById('fusion-conflict-alert');
    const conflictList = document.getElementById('fusion-conflict-list');
    if (conflictAlert && conflictList) {
      if (fusion.conflicts && fusion.conflicts.length > 0) {
        conflictAlert.classList.remove('hidden');
        conflictList.innerHTML = '';
        fusion.conflicts.forEach(c => {
          const item = document.createElement('div');
          item.className = 'flex items-start gap-2 bg-black/20 p-2 rounded-lg';
          item.innerHTML = `<span class="font-bold text-amber-300">•</span> <span><strong>${c.source_a}</strong> identified <em>${c.material_a}</em>, whereas <strong>${c.source_b}</strong> reported <em>${c.material_b}</em>.</span>`;
          conflictList.appendChild(item);
        });
      } else {
        conflictAlert.classList.add('hidden');
      }
    }

    // Evidence grid
    const evidenceGrid = document.getElementById('fusion-evidence-grid');
    if (evidenceGrid) {
      evidenceGrid.innerHTML = '';
      const evidenceItems = fusion.supporting_evidence || [];
      evidenceItems.forEach(ev => {
        const tile = document.createElement('div');
        tile.className = 'p-3 rounded-xl bg-slate-800/80 border border-slate-700/80 space-y-1 text-xs';
        tile.innerHTML = `
          <div class="flex items-center justify-between text-[11px] font-bold text-teal-300">
            <span>${ev.source}</span>
            <span class="text-slate-400 font-normal">${ev.object_name || ''}</span>
          </div>
          <div class="font-semibold text-white truncate">${ev.material || 'Material Detected'}</div>
          ${ev.label_text_snippet ? `<div class="text-[10px] text-slate-400 italic font-mono truncate">"${ev.label_text_snippet}"</div>` : ''}
          ${ev.manufacturer ? `<div class="text-[10px] text-slate-400 truncate">${ev.manufacturer}</div>` : ''}
        `;
        evidenceGrid.appendChild(tile);
      });
    }

    // User confirmation box
    const confirmBox = document.getElementById('fusion-confirm-box');
    if (confirmBox) {
      if (fusion.needs_user_confirmation) {
        confirmBox.classList.remove('hidden');
      } else {
        confirmBox.classList.add('hidden');
      }
    }
  }

  // ================= POPULATE "WHAT WE READ" OCR SECTION =================
  const ocrCard = document.getElementById('ocr-section-card');
  const ocrEvidence = data.ocr_evidence || {};
  const imgQuality = data.image_quality || {};

  if (ocrCard) {
    // If text analysis without packaging image, adjust card presentation
    if (data.input_method === 'text_description' && !ocrEvidence.extracted_text) {
      ocrCard.classList.add('hidden');
    } else {
      ocrCard.classList.remove('hidden');

      // OCR Quality & Confidence Badges
      const qualBadge = document.getElementById('ocr-quality-badge');
      const confBadge = document.getElementById('ocr-confidence-badge');
      const qualAlert = document.getElementById('ocr-quality-alert');
      const qualTitle = document.getElementById('ocr-quality-title');
      const qualText = document.getElementById('ocr-quality-text');

      if (qualBadge) {
        qualBadge.textContent = `Image: ${imgQuality.status || 'Good'}`;
      }
      if (confBadge) {
        const confPct = Math.round((ocrEvidence.ocr_confidence || 0.92) * 100);
        confBadge.textContent = `${confPct}% OCR Confidence`;
      }

      // Show quality warning if blurry, dark, or low contrast
      if (qualAlert) {
        if (imgQuality.is_blurry || imgQuality.is_dark || imgQuality.is_low_contrast || imgQuality.is_overexposed) {
          qualTitle.textContent = `${imgQuality.status} detected:`;
          qualText.textContent = imgQuality.guidance || 'Please capture a sharper image with even lighting for maximum OCR accuracy.';
          qualAlert.classList.remove('hidden');
        } else {
          qualAlert.classList.add('hidden');
        }
      }

      // Detected Symbols
      const symContainer = document.getElementById('ocr-symbols-container');
      if (symContainer) {
        symContainer.innerHTML = '';
        const symbols = ocrEvidence.detected_symbols || ['♳ (PET 1)'];
        symbols.forEach(sym => {
          const pill = document.createElement('span');
          pill.className = 'px-2 py-0.5 rounded-md text-xs font-extrabold bg-eco-500/20 text-eco-300 border border-eco-500/30';
          pill.textContent = sym;
          symContainer.appendChild(pill);
        });
      }

      // Identified Material & Source
      const idMat = document.getElementById('ocr-identified-material');
      const idSrc = document.getElementById('ocr-source');
      if (idMat) idMat.textContent = ocrEvidence.identified_material || analysis.primary_material || 'Polyethylene Terephthalate (PET, #1)';
      if (idSrc) idSrc.textContent = `Source: ${ocrEvidence.information_source || 'Molded container base stamp'}`;

      // Raw Extracted Text
      const rawTextElem = document.getElementById('ocr-extracted-text');
      if (rawTextElem) {
        rawTextElem.textContent = ocrEvidence.extracted_text || 'No printed alphanumeric text detected on packaging surface.';
      }

      // Barcode / QR Registry Evidence Card
      const resBarcodeCard = document.getElementById('res-barcode-card');
      const barcodeEvidence = data.barcode_evidence;
      if (resBarcodeCard) {
        if (barcodeEvidence && barcodeEvidence.barcode) {
          resBarcodeCard.classList.remove('hidden');
          document.getElementById('res-barcode-num').textContent = barcodeEvidence.barcode;
          document.getElementById('res-barcode-title').textContent = barcodeEvidence.verified ? 'Verified Barcode Match' : (barcodeEvidence.manual_correction_applied ? 'User Specified Product' : 'Unregistered Barcode');
          document.getElementById('res-barcode-brand').textContent = barcodeEvidence.brand_owner || barcodeEvidence.manufacturer || 'Manual Correction';
          document.getElementById('res-barcode-registry').textContent = barcodeEvidence.source || 'EcoTransform Verified Packaging Database';
        } else {
          resBarcodeCard.classList.add('hidden');
        }
      }
    }
  }

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
  setScannerMode('upload');
  renderImagePreview(dataUrl);
  showActivePreviewBadge(dataUrl, item.name, 'Preset Sample Loaded');
  validateScannerForm();

  // Trigger analysis immediately for lightning demo
  setTimeout(() => {
    submitUnifiedAnalysis();
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
