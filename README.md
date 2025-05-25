![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)

# MineWatch AI - PH 🇵🇭

**MineWatch AI - PH** is a drone footage analysis system tailored for **Philippine mining conditions**. Built with Python 3.11, OpenCV, and GPT API integration, it extracts video frames and analyzes them using site-specific context. This tool is built for environmental monitoring, site assessments, and compliance checks—factoring in the unique challenges of tropical weather and local mining practices.

---

## 🔍 What It Does

- 🎥 **Extracts key frames** from drone video footage  
- 🤖 **Sends images and mining context** to a GPT-based API for environmental analysis  
- 📌 Focused on **PH-specific issues** like water discoloration, tailings overflow, and erosion

---

## 🎯 Current Milestone Objectives

#### 🔧 1. Run Analysis Button UX
- [ ] Disable other buttons while analysis is running.
- [ ] Show a loading indicator or spinner during the process.
- [ ] Prevent re-triggering of analysis mid-run.

#### 🧠 2. LangChain Pipeline Refactor
- [ ] Add **nested chains**: one per frame, analyzing multiple risk factors.
- [ ] Implement a **meta-chain** to summarize across frames for a complete report.
- [ ] Store all AI outputs and user prompts for RAG-style chatbot use.
- [ ] Prototype chatbot that responds based on stored site analysis data.

#### 🖼️ 3. Add Frame Support
- [ ] Enable manual frame **insertion** in case of skipped or poor-quality frames.
- [ ] Integrate added frames into the existing pipeline seamlessly.

#### 🎨 4. UI/UX Enhancement
- [ ] Refactor layout and component design for clarity and ease of use.
- [ ] Group features visually for intuitive flow (e.g., upload > extract > analyze).
- [ ] Add basic frontend polish or outsource UI work to a frontend dev.

## ⚙️ Setup Instructions

```bash
# Clone and enter the repo
git clone https://github.com/your-username/minewatch-ai-PH.git
cd minewatch-ai-PH

# Create virtual environment
python3.11 -m venv minewatch-venv
source minewatch-venv/bin/activate     # Windows: minewatch-venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

> 💡 Edit `src/config.py` to add your GPT API key and modify site-specific context.

---

## 🚀 Run the System
Nothing here yet to update hehehe

---

## 🇵🇭 Local Optimization

This version is adapted specifically for:
- **Tropical environments** and **seasonal rainfall patterns**
- Open-pit and small-scale mining common in the Philippines
- Environmental indicators often observed in PH drone surveys

---

## 🔮 Future Roadmap

- 🌐 Dashboard for visual analysis
- 📡 Weather-aware frame tagging (rain, flooding)
- 📑 Auto-generate reports aligned with **DENR** or **EMB** guidelines

---

## 📜 License

MineWatch AI - PH © 2025 by **Axcel Justin D. Tidalgo** is licensed under the  
**Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

🔗 [View License](https://creativecommons.org/licenses/by-nc-sa/4.0/)

---
