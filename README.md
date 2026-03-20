# Group_G — Project Okavango

Project Okavango is a lightweight environmental data analysis tool built for the detection and visualization of at risk natural regions of the world. The project integrates geospatial data with the most recent environmental datasets to analyze and visualize global forest change, land degradation, and ecosystem protection. Results are presented through an interactive Streamlit web application powered by AI driven satellite image analysis.

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

        git clone https://github.com/Behnia02/Group_G.git
        cd Group_G

2. Install Python dependencies:

        pip install -r requirements.txt

3. Pull the required Ollama model:

        ollama pull llava:7b

4. Run the app:

        python -m streamlit run app/streamlit_app.py

## How to Run the Streamlit App

    python -m streamlit run app/streamlit_app.py

The app has two pages:
- **Environmental Explorer** — interactive world map with 5 environmental indicators
- **AI Workflow** — satellite image download and AI environmental risk assessment

## Examples of Environmental Risk Detection

### Example 1 — Amazon Basin, Brazil (HIGH Risk)
**Coordinates:** -6.64, -51.99 — Zoom 9

![Amazon Basin deforestation](assets/example1_amazon.jpeg)

**AI Description:** Aerial view with patches of dark green vegetation, bare soil, and visible road networks cutting through the landscape. Clear signs of forest fragmentation and land conversion.

**Risk Assessment:** HIGH: Annual deforestation and forest area change both suggest elevated concern. Dataset context score: 0.60.

---

### Example 2 — Aral Sea, Kazakhstan (MODERATE Risk)
**Coordinates:** 45.1, 59.0 — Zoom 9

![Aral Sea desiccation](assets/example2_aral.jpeg)

**AI Description:** Satellite view of a dramatically dried-up lake surrounded by arid desert terrain. The lake is now largely covered in algae, indicating severe water quality degradation and one of the worst ecological disasters in history.

**Risk Assessment:** MODERATE: Land degradation suggests elevated concern. Land protected and mountain ecosystems add moderate context risk. Dataset context score: 0.52.

---

### Example 3 — Atacama Desert, Chile (MODERATE Risk)
**Coordinates:** -22.3, -68.9 — Zoom 10

![Atacama Desert mining](assets/example3_atacama.jpeg)

**AI Description:** Desert landscape with rocky terrain, sparse vegetation, exposed rock and sand, eroded terrain, and visible structures suggesting mining activity in the centre of the image.

**Risk Assessment:** MODERATE: Annual deforestation suggests elevated concern. Forest area change adds moderate context risk. Dataset context score: 0.46.

---

## SDGs and Project Impact

Project Okavango was built as a proof of concept for environmental monitoring using open data and local AI models. The tool combines satellite imagery, geospatial datasets, and large language models to identify at risk natural regions anywhere in the world.

The world is facing an accelerating environmental crisis. Forests are disappearing at unprecedented rates, land is being degraded faster than it can recover, and ecosystems that took millennia to form are being destroyed within decades. Traditional monitoring approaches rely on expensive satellite infrastructure, proprietary software, and specialised expertise that many organisations and governments simply do not have access to. Project Okavango demonstrates that meaningful environmental monitoring does not have to be expensive or inaccessible.

### SDG 15 — Life on Land
This is the most direct connection. The project monitors deforestation, land degradation, ecosystem protection, and mountain biodiversity. The three examples above each illustrate a different dimension of land based environmental threat.

### SDG 13 — Climate Action
Deforestation and land degradation are major drivers of climate change. By flagging areas experiencing active forest loss, the tool contributes to early warning systems that can inform climate action at local and national levels.

### SDG 17 — Partnerships for the Goals
The project is built entirely on free and open data sources and open-source tools, demonstrating how lightweight accessible tools can be built without proprietary software, enabling wider adoption in lower resource contexts.

### SDG 11 — Sustainable Cities and Communities
The AI Workflow allows users to analyse any location on Earth, including peri urban areas where natural land is being converted to urban use, supporting urban planners in monitoring the environmental impact of city growth.

In summary, Project Okavango demonstrates how open data, geospatial analysis, and local AI models can be combined into a lightweight tool with real world environmental monitoring applications. With further development, this type of tool could support NGOs, government agencies, and researchers in tracking progress towards the SDGs in near real time.
