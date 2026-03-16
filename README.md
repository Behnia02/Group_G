# Group_G — Project Okavango

Project Okavango is a lightweight environmental data analysis tool built for the detection and visualization of at-risk natural regions of the world. The project integrates geospatial data with the most recent environmental datasets to analyze and visualize global forest change, land degradation, and ecosystem protection. Results are presented through an interactive Streamlit web application powered by AI-driven satellite image analysis.

## Group Members

| Name | Student Number | Email |
|---|---|---|
| João Caseiro | 56517 | joaommcaseiro@gmail.com |
| Catarina Palma | 56526 | catarinapalma01@gmail.com |
| Afonso João | 72008 | ajabjoao@gmail.com |
| Behnia Ghadiani | 71819 | 71819@novabse.pt |

## Installation

### Requirements
- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running locally

### Steps

1. Clone the repository:
```bash
git clone https://github.com/Behnia02/Group_G.git
cd Group_G
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Pull the required Ollama model:
```bash
ollama pull llava:7b
```

4. Run the app:
```bash
python -m streamlit run app/streamlit_app.py
```

## How to Run the Streamlit App
```bash
python -m streamlit run app/streamlit_app.py
```

The app has two pages:
- **Environmental Explorer** — interactive world map with 5 environmental indicators
- **AI Workflow** — satellite image download and AI environmental risk assessment

## SDGs and Project Impact

### SDG 15 — Life on Land
This is the most direct connection. The project monitors deforestation, land degradation, ecosystem protection, and mountain biodiversity. By combining satellite imagery with historical environmental datasets, the tool enables rapid identification of at-risk regions.

### SDG 13 — Climate Action
Deforestation and land degradation are major drivers of climate change. By flagging areas experiencing active forest loss, the tool contributes to early warning systems that can inform climate action at local and national levels.

### SDG 17 — Partnerships for the Goals
The project is built entirely on free and open data sources and open-source tools, demonstrating how lightweight accessible tools can be built without proprietary software.

### SDG 11 — Sustainable Cities and Communities
The AI Workflow allows users to analyse any location on Earth, including peri-urban areas where natural land is being converted to urban use, supporting urban planners in monitoring environmental impact.

In summary, Project Okavango demonstrates how open data, geospatial analysis, and local AI models can be combined into a lightweight tool with real-world environmental monitoring applications.
