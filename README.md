# MineWatch AI - PH 🇵🇭

**MineWatch AI - PH** is a drone footage analysis system tailored for **Philippine mining conditions**. Built with Python 3.11, OpenCV, and GPT API integration, it extracts video frames and analyzes them using site-specific context. This tool is built for environmental monitoring, site assessments, and compliance checks—factoring in the unique challenges of tropical weather and local mining practices.

---

## 🔍 What It Does

- 🎥 **Extracts key frames** from drone video footage  
- 🤖 **Sends images and mining context** to a GPT-based API for environmental analysis  
- 📌 Focused on **PH-specific issues** like water discoloration, tailings overflow, and erosion

---

## ⚙️ Setup Instructions

```bash
# Clone and enter the repo
git clone https://github.com/your-username/minewatch-ai-PH.git
cd minewatch-ai-PH

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

> 💡 Edit `src/config.py` to add your GPT API key and modify site-specific context.

---

## 🚀 Run the System

```bash
python src/main.py
```

The script will:
1. Extract frames from your drone video
2. Analyze each frame with your GPT API
3. Save the results to a `.txt` file

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
