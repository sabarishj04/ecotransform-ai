# 🌱 EcoTransform AI — AI-Powered Waste-to-Wealth Intelligence Platform

> **"Turning Today's Trash into Tomorrow's Cash"**  
> An AI-driven web application that scans discarded materials, classifies recyclability streams, calculates avoided carbon and landfill metrics, and generates **actionable, monetizable DIY transformation blueprints**.

---

## 🚀 Quick Start (Running Locally)

### 1. Start the Application
Open your terminal in `scratch/ecotransform-ai` and run:

```bash
cd scratch/ecotransform-ai
python app.py
```

Open your browser to: **`http://127.0.0.1:8000`**

### 2. Optional: Enable Live Google Gemini Vision
By default, the platform includes an **Intelligent Offline Heuristic Analyzer** so it works 100% reliably with zero setup. To connect live Google Gemini 1.5/2.0 Flash:

```bash
# In Windows PowerShell:
$env:GEMINI_API_KEY="your-gemini-api-key-here"
python app.py
```

---

## 🌐 How to Make It a Public Website (Accessible by Anyone Worldwide)

You have **3 simple, free options** to share your live website with hackathon judges or teammates:

### Option A: Instant Free Public URL via Pinggy / Localtunnel (Fastest for Demos)
Run this command in a second terminal while your `python app.py` is running on port 8000:

```bash
# Using Pinggy (no installation required):
ssh -p 443 -R0:localhost:8000 a.pinggy.io
```
Or using **ngrok**:
```bash
ngrok http 8000
```
This generates an instant HTTPS public link (e.g. `https://xxxx.a.pinggy.link` or `https://xxxx.ngrok-free.app`) that works on **any phone or computer in the world!**

---

### Option B: 100% Free Cloud Hosting on Render.com (Permanent Public Link)
1. Push this folder to a GitHub repository.
2. Go to [Render.com](https://render.com) and click **New Web Service**.
3. Select your GitHub repository.
4. Render will auto-detect `render.yaml` or you can enter:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. Click **Deploy**. In ~2 minutes you have a permanent public URL: `https://ecotransform-ai.onrender.com`!

---

### Option C: 1-Click Deploy on Railway.app
1. Go to [Railway.app](https://railway.app).
2. Connect your GitHub repository.
3. Railway automatically detects `Dockerfile` and deploys your public HTTPS application.

---

## 🎯 Key Hackathon Features Implemented

1. **Multimodal Waste Scanning:** Drag-and-drop image upload or live WebRTC mobile/webcam snapshot.
2. **Instant 1-Click Demo Presets:** Pre-loaded buttons on the homepage for Plastic Bottles, Aluminum Soda Cans, Cardboard Boxes, and Batteries so judges can test instantly without needing to take a photo.
3. **5-Stream Classification:** Evaluates Recyclable, Reusable, Biodegradable, Hazardous, and Non-recyclable.
4. **Waste-to-Wealth Blueprints:** 3 graded upcycling recipes (Beginner, Intermediate, Artisan) with step-by-step instructions, tools needed, safety warnings, and estimated profit ROI ($).
5. **EPA WARM Carbon Calculator:** Calculates actual avoided emissions (kg CO₂e), landfill mass diverted (kg), and water conserved (liters).
6. **Sustainability Dashboard:** Real-time KPI counters, material breakdown donut chart, and real-world equivalencies (trees planted, car miles saved).
7. **Scan History:** Persistent SQLite ledger with search filtering and detailed recipe recall.
8. **Safety Override for Hazardous Materials:** Locks DIY recipes for batteries or chemicals and provides certified municipal disposal protocols.
