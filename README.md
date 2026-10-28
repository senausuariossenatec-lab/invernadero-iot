# 🌱 Invernadero IoT

Microinvernadero inteligente que monitorea temperatura, humedad del aire, humedad de suelo, luz y nivel del depósito, y controla automáticamente el riego, la ventilación y la iluminación.

**PROGRAMA SENATIC 2026 - IEM ARTEMIO MENDOZA**
Técnico en Implementación y Mantenimiento de Sistemas de Internet de las Cosas · Grupo 3147083

## Flujo de datos
Wokwi (ESP32) → ThingSpeak (8 campos) → GitHub (este repositorio) → Streamlit (dashboard)

## Archivos
- `app.py` – dashboard en Streamlit
- `requirements.txt` – librerías de Python
- `wokwi/sketch.ino`, `wokwi/diagram.json`, `wokwi/libraries.txt` – simulación del ESP32

## Equipo
Maria Angelica Argoty Gaitan (líder), Jenifer Alexandra Insuasty Mafla, Vanessa Paola Portillo Pardo, Eilin Estefania Achicanoy Enriquez, Marlon Alejandro Eraso Baca.
Instructor: James Betancourt.
