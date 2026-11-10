# 📸 SnapClass — AI-Based Smart Attendance Automation System

<div align="center">

  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV" />
  <img src="https://img.shields.io/badge/Dlib-Computer_Vision-0284C7?style=for-the-badge" alt="Dlib" />

  <p align="center">
    <strong>Full-Stack Automated Student Attendance Verification via Real-Time Computer Vision & Cloud Synchronization.</strong>
  </p>

</div>

---

## 📌 Project Overview
**SnapClass** eliminates proxy attendance, paper records, and manual roll-calling in academic institutions. Utilizing real-time video frames from standard webcams, SnapClass detects facial landmarks using **Dlib**, compares feature vectors against enrolled student embeddings, and logs verified attendance records to a **Supabase PostgreSQL** cloud database in milliseconds.

---

## ✨ Flagship Capabilities
- **Real-Time Facial Recognition:** High-accuracy 68-point facial landmark localization and 128-dimensional biometric embedding generation via Dlib and OpenCV.
- **Cloud-Native Record Keeping:** Relational tables on **Supabase** maintain student rosters, timestamps, section IDs, and attendance percentages.
- **Interactive Instructor Portal:** Zero-friction **Streamlit** dashboard enabling teachers to view live recognition streams, trigger attendance sessions, and export reports.
- **Automated Analytics & Reporting:** Instant export of attendance metrics to Excel/CSV with visual attendance breakdown charts.
- **Docker Ready:** Includes production `Dockerfile` for streamlined containerized deployment.

---

## 🏗️ Computer Vision Pipeline

```text
[ Live Webcam Feed ]
         │
         ▼
[ Frame Capture & Grayscale Conversion ]
         │
         ▼
[ Dlib HOG Face Detector ]
         │
         ▼
[ 68-Point Facial Landmark Localization ]
         │
         ▼
[ 128-D Biometric Embedding Generation ]
         │
         ▼
[ Euclidean Distance Vector Matching ]
         │
  ┌──────┴────────────────┐
  │ Known Match Found?    │
  └──────┬────────────────┘
         ├── YES ──► Log Attendance to Supabase PostgreSQL (Timestamped)
         └── NO  ──► Mark Unknown / Alert Instructor
```

---

## 🚀 Setup & Execution

### 1. Clone & Enter Repository
```bash
git clone https://github.com/tanisha162/SNAPCLASS.git
cd SNAPCLASS
```

### 2. Environment Setup
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Supabase Credentials
Create `.env` in the project root:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 4. Run Application
```bash
streamlit run app.py
```

---

## 👩‍💻 Author & Connect
**Tanisha Gupta** — Full-Stack Developer & AI/ML Engineer  
- **GitHub:** [@tanisha162](https://github.com/tanisha162)  
- **LinkedIn:** [linkedin.com/in/tanisha-gupta162](https://www.linkedin.com/in/tanisha-gupta162)  
- **Email:** [gtanisha162@gmail.com](mailto:gtanisha162@gmail.com)
