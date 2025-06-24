# 📊 ATS Recruitment Dashboard

Een krachtige Streamlit applicatie voor het analyseren van ATS (Applicant Tracking System) export data. Upload je CSV bestand en krijg direct uitgebreide recruitment analytics.

## 🚀 Features

- **📈 Vacaturestatus Overzicht**: Real-time inzicht in openstaande, vervulde en niet-vervulde posities
- **👥 Recruiter Performance**: Analyseer prestaties van individuele recruiters
- **🌐 Kanaal Effectiviteit**: Ontdek welke wervingskanalen het beste converteren
- **📅 Tijdlijn Analyse**: Bekijk trends en patronen over tijd
- **🔍 Interactive Dashboards**: Volledig interactieve charts en tabellen
- **📱 Responsive Design**: Werkt perfect op desktop en mobile

## 🎯 Mogelijke Inzichten

### ✅ Volledig Ondersteund
- Aantal openstaande/gesloten rollen per periode
- Fill rate per recruiter en overall
- Kanaal performance en conversie ratio's
- Status verdelingen en trends
- Demografische analyses op vacature-niveau

### ⚠️ Beperkt Ondersteund  
- Doorlooptijd analyses (afhankelijk van beschikbare datumvelden)
- Tijdlijn trends (vereist langere dataset periode)

## 🛠️ Installatie & Gebruik

### Lokaal Draaien

```bash
# Clone de repository
git clone https://github.com/jouw-username/ats-dashboard.git
cd ats-dashboard

# Installeer dependencies
pip install -r requirements.txt

# Start de applicatie
streamlit run app.py
```

### Online Deployment (Streamlit.io)

1. Fork deze repository naar je eigen GitHub account
2. Ga naar [share.streamlit.io](https://share.streamlit.io)
3. Verbind je GitHub account
4. Selecteer je repository en branch
5. Set main file path naar `app.py`
6. Deploy!

## 📁 Data Formaat

De applicatie verwacht een CSV export uit je ATS systeem met minimaal de volgende kolommen:

### Verplichte Velden
- `Functie` - Vacaturetitel
- `Status vacature` - Huidige status (Extern vervuld, Intern vervuld, etc.)
- `Eigenaar` - Verantwoordelijke recruiter
- `Aantal reacties` - Totaal aantal sollicitaties

### Optionele Velden  
- `Datum aanmaak` - Voor tijdlijn analyses
- `Totaal per wervingskanaal: [KANAAL]` - Voor kanaal analyses
- `Totaal per wervingskanaal (aangenomen): [KANAAL]` - Voor conversie berekeningen
- Demografische velden (leeftijd, geslacht, nationaliteit)

### Ondersteunde Formats
- **Delimiter**: Puntkomma (;) 
- **Encoding**: UTF-8, CP1252, ISO-8859-1, Latin-1
- **Datumformaat**: DD-MM-YYYY

## 🔧 Technische Details

### Dependencies
- **Streamlit**: Web framework voor de dashboard interface
- **Pandas**: Data manipulatie en analyse  
- **Plotly**: Interactieve visualisaties
- **NumPy**: Numerieke berekeningen

### Architecture
```
app.py                 # Main Streamlit application
├── load_and_process_data()    # CSV parsing met multiple encoding support
├── calculate_metrics()        # KPI berekeningen
├── create_status_chart()      # Status verdeling visualisatie
├── create_recruiter_performance_chart()  # Recruiter analyses
├── create_channel_analysis()  # Wervingskanaal effectiviteit  
└── create_timeline_analysis() # Tijdlijn trends
```

## 📊 Dashboard Screenshots

### Status Overzicht
- Pie chart van vacaturestatus verdeling
- KPI cards met key metrics
- Gedetailleerde status tabel

### Recruiter Performance  
- Bar charts van vacatures per recruiter
- Fill rate vergelijkingen
- Performance tabellen

### Kanaal Analyse
- Sollicitanten per kanaal
- Conversie ratio's per kanaal
- ROI analyses

## 🤝 Contributing

Contributions zijn welkom! Om bij te dragen:

1. Fork de repository
2. Maak een feature branch (`git checkout -b feature/nieuwe-feature`)
3. Commit je wijzigingen (`git commit -am 'Voeg nieuwe feature toe'`)
4. Push naar de branch (`git push origin feature/nieuwe-feature`)
5. Maak een Pull Request

## 🐛 Bug Reports & Feature Requests

Heb je een bug gevonden of een idee voor een nieuwe feature? 
[Open een issue](https://github.com/jouw-username/ats-dashboard/issues) op GitHub.

## 📝 License

Dit project valt onder de MIT License - zie het [LICENSE](LICENSE) bestand voor details.

## 🙏 Acknowledgments

- Gebouwd met [Streamlit](https://streamlit.io/)
- Visualisaties door [Plotly](https://plotly.com/)
- Data processing met [Pandas](https://pandas.pydata.org/)

---

**🚀 Ready to get insights from your recruitment data? Upload your CSV and start analyzing!**
