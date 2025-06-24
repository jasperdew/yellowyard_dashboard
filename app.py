import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta, date
import io

# Configuratie van de pagina
st.set_page_config(
    page_title="ATS Recruitment Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS voor betere styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-metric {
        border-left-color: #2ca02c;
    }
    .warning-metric {
        border-left-color: #ff7f0e;
    }
    .danger-metric {
        border-left-color: #d62728;
    }
    .action-item {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.25rem;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    .urgent-action {
        background-color: #f8d7da;
        border-color: #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

def load_and_process_data(uploaded_file):
    """Laadt en verwerkt de ATS CSV data"""
    try:
        # Probeer verschillende encodings
        encodings = ['utf-8', 'cp1252', 'iso-8859-1', 'latin-1']
        df = None
        
        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=encoding, delimiter=';')
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            st.error("Kon bestand niet inlezen. Controleer de encoding.")
            return None
        
        # Data cleaning
        df.columns = df.columns.str.strip()
        
        # Converteer datums - probeer verschillende formaten
        date_columns = ['Datum aanmaak', 'Startdatum intern', 'Einddatum intern', 
                       'Startdatum extern', 'Einddatum extern']
        
        for col in date_columns:
            if col in df.columns:
                # Probeer verschillende datum formaten
                df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')
                if df[col].isna().all():
                    df[col] = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')
        
        # Vervang 0000-00-00 datums met NaT
        for col in date_columns:
            if col in df.columns:
                df.loc[df[col].dt.year == 1900, col] = pd.NaT
        
        # Bereken dagen sinds aanmaak voor elk record
        if 'Datum aanmaak' in df.columns:
            today = pd.Timestamp.now()
            df['Dagen_Sinds_Aanmaak'] = (today - df['Datum aanmaak']).dt.days
        
        # Status categoriseren voor betere filtering
        df['Status_Categorie'] = df['Status vacature'].map({
            'Extern vervuld': 'Vervuld',
            'Intern vervuld': 'Vervuld', 
            'Niet vervuld': 'Gesloten',
            'Ingetrokken': 'Gesloten',
            'Publicatie in- en extern': 'Actief',
            'Publicatie intern': 'Actief',
            'In procedure': 'Actief',
            'Intake': 'In Voorbereiding',
            'Tekst bij vacaturehouder': 'In Voorbereiding',
            'Aangemaakt': 'In Voorbereiding',
            'Talentpool': 'Geparkeerd'
        })
        
        return df
    
    except Exception as e:
        st.error(f"Fout bij het laden van data: {str(e)}")
        return None

def filter_data_by_date(df, start_date, end_date, date_column='Datum aanmaak'):
    """Filtert data op basis van geselecteerde datumrange"""
    if date_column not in df.columns:
        return df
    
    mask = (df[date_column] >= pd.Timestamp(start_date)) & (df[date_column] <= pd.Timestamp(end_date))
    return df.loc[mask]

def get_actionable_insights(df, period_df):
    """Genereert actionable insights en aanbevelingen"""
    insights = []
    
    # 1. Vacatures die te lang open staan
    long_open = period_df[
        (period_df['Status_Categorie'] == 'Actief') & 
        (period_df['Dagen_Sinds_Aanmaak'] > 30)
    ]
    
    if len(long_open) > 0:
        insights.append({
            'type': 'urgent',
            'title': f'🚨 {len(long_open)} vacatures staan >30 dagen open',
            'description': f'Deze vacatures hebben mogelijk problemen met de job description, salaris of targeting.',
            'action': 'Review job requirements en overweeg aanpassingen aan salaris/benefits',
            'data': long_open[['Functie', 'Eigenaar', 'Dagen_Sinds_Aanmaak', 'Aantal reacties']].head(5)
        })
    
    # 2. Vacatures zonder reacties
    no_responses = period_df[
        (period_df['Status_Categorie'] == 'Actief') & 
        (period_df['Aantal reacties'] == 0) &
        (period_df['Dagen_Sinds_Aanmaak'] > 7)
    ]
    
    if len(no_responses) > 0:
        insights.append({
            'type': 'warning',
            'title': f'⚠️ {len(no_responses)} actieve vacatures zonder reacties',
            'description': 'Deze vacatures genereren geen interesse van kandidaten.',
            'action': 'Check job posting visibility, herformuleer job description of verhoog budget',
            'data': no_responses[['Functie', 'Eigenaar', 'Dagen_Sinds_Aanmaak']].head(5)
        })
    
    # 3. Top performing recruiters
    recruiter_performance = period_df.groupby('Eigenaar').agg({
        'Functie': 'count',
        'Status_Categorie': lambda x: (x == 'Vervuld').sum(),
        'Aantal reacties': 'mean'
    }).rename(columns={'Functie': 'Totaal', 'Status_Categorie': 'Vervuld'})
    
    recruiter_performance['Fill_Rate'] = (recruiter_performance['Vervuld'] / recruiter_performance['Totaal'] * 100).round(1)
    top_performer = recruiter_performance[recruiter_performance['Totaal'] >= 3].sort_values('Fill_Rate', ascending=False).head(1)
    
    if len(top_performer) > 0:
        best_recruiter = top_performer.index[0]
        fill_rate = top_performer['Fill_Rate'].iloc[0]
        insights.append({
            'type': 'success',
            'title': f'🏆 Top performer: {best_recruiter}',
            'description': f'Fill rate van {fill_rate}% in deze periode.',
            'action': f'Analyseer werkwijze van {best_recruiter} en deel best practices met team',
            'data': recruiter_performance.sort_values('Fill_Rate', ascending=False).head(3)
        })
    
    # 4. Kanalen met lage conversie
    channels = ['V&VN', 'Indeed', 'Infopuntzorg', 'Zorgselect', 'Facebook', 'Linkedin']
    channel_performance = []
    
    for channel in channels:
        total_col = f'Totaal per wervingskanaal: {channel}'
        hired_col = f'Totaal per wervingskanaal (aangenomen): {channel}'
        
        if total_col in period_df.columns and hired_col in period_df.columns:
            total = period_df[total_col].sum()
            hired = period_df[hired_col].sum()
            if total > 10:  # Alleen kanalen met significante volumes
                conversion = (hired / total * 100) if total > 0 else 0
                channel_performance.append({
                    'Kanaal': channel,
                    'Totaal': total,
                    'Conversie': conversion
                })
    
    if channel_performance:
        channel_df = pd.DataFrame(channel_performance)
        low_performing = channel_df[channel_df['Conversie'] < 5]  # < 5% conversie
        
        if len(low_performing) > 0:
            insights.append({
                'type': 'warning',
                'title': f'📉 {len(low_performing)} kanalen met lage conversie (<5%)',
                'description': 'Deze kanalen genereren veel kandidaten maar weinig hires.',
                'action': 'Optimaliseer targeting of overweeg budget herverdeling naar betere kanalen',
                'data': low_performing
            })
    
    return insights

def create_daily_activity_chart(df, date_range):
    """Maakt een daily activity chart voor de geselecteerde periode"""
    start_date, end_date = date_range
    
    # Maak een complete datumrange
    date_range_full = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Nieuwe vacatures per dag
    new_jobs = df.groupby(df['Datum aanmaak'].dt.date)['Functie'].count().reindex(
        [d.date() for d in date_range_full], fill_value=0
    )
    
    # Vervulde vacatures per dag (op basis van status)
    filled_jobs = df[df['Status_Categorie'] == 'Vervuld'].groupby(
        df['Datum aanmaak'].dt.date
    )['Functie'].count().reindex([d.date() for d in date_range_full], fill_value=0)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=new_jobs.index,
        y=new_jobs.values,
        mode='lines+markers',
        name='Nieuwe Vacatures',
        line=dict(color='blue', width=2),
        fill='tonexty'
    ))
    
    fig.add_trace(go.Scatter(
        x=filled_jobs.index,
        y=filled_jobs.values,
        mode='lines+markers',
        name='Vervulde Vacatures',
        line=dict(color='green', width=2),
        fill='tonexty'
    ))
    
    fig.update_layout(
        title='Dagelijkse Vacature Activiteit',
        xaxis_title='Datum',
        yaxis_title='Aantal Vacatures',
        height=400,
        hovermode='x unified'
    )
    
    return fig

def create_vacancy_performance_table(df):
    """Maakt gedetailleerde vacancy performance tabel"""
    performance_data = []
    
    for _, row in df.iterrows():
        # Bereken performance score op basis van verschillende factoren
        score = 0
        factors = []
        
        # Factor 1: Tijd sinds aanmaak
        if row['Dagen_Sinds_Aanmaak'] <= 14:
            score += 30
            factors.append("Nieuw (≤14 dagen)")
        elif row['Dagen_Sinds_Aanmaak'] <= 30:
            score += 20
            factors.append("Recent (≤30 dagen)")
        else:
            score += 5
            factors.append(f"Lang open ({row['Dagen_Sinds_Aanmaak']} dagen)")
        
        # Factor 2: Aantal reacties vs tijd
        expected_responses = max(1, row['Dagen_Sinds_Aanmaak'] * 0.5)  # 0.5 reacties per dag verwacht
        if row['Aantal reacties'] >= expected_responses * 1.5:
            score += 40
            factors.append("Hoge interesse")
        elif row['Aantal reacties'] >= expected_responses:
            score += 25
            factors.append("Gemiddelde interesse")
        else:
            score += 10
            factors.append("Lage interesse")
        
        # Factor 3: Status
        if row['Status_Categorie'] == 'Vervuld':
            score += 30
            factors.append("Succesvol vervuld")
        elif row['Status_Categorie'] == 'Actief':
            score += 20
            factors.append("Actief in procedure")
        else:
            score += 5
        
        performance_data.append({
            'Functie': row['Functie'][:50] + '...' if len(row['Functie']) > 50 else row['Functie'],
            'Status': row['Status vacature'],
            'Eigenaar': row['Eigenaar'],
            'Dagen Open': row['Dagen_Sinds_Aanmaak'],
            'Reacties': row['Aantal reacties'],
            'Performance Score': min(100, score),
            'Factoren': ' | '.join(factors[:2])
        })
    
    return pd.DataFrame(performance_data).sort_values('Performance Score', ascending=False)

def main():
    st.title("📊 ATS Recruitment Dashboard")
    st.markdown("**Actionable recruitment analytics met datum-filtering**")
    
    # Sidebar voor configuratie
    with st.sidebar:
        st.header("⚙️ Dashboard Configuratie")
        
        uploaded_file = st.file_uploader(
            "Upload ATS CSV bestand",
            type=['csv'],
            help="Upload het CSV bestand geëxporteerd uit je ATS systeem"
        )
        
        if uploaded_file:
            st.success("✅ Data geladen!")
    
    if uploaded_file is not None:
        # Laad data
        with st.spinner('Data aan het verwerken...'):
            df = load_and_process_data(uploaded_file)
        
        if df is not None and 'Datum aanmaak' in df.columns:
            # Datum filter in sidebar
            with st.sidebar:
                st.subheader("📅 Periode Selectie")
                
                min_date = df['Datum aanmaak'].min().date()
                max_date = df['Datum aanmaak'].max().date()
                
                # Voorgedefinieerde periodes
                today = date.today()
                period_options = {
                    "Laatste 7 dagen": (today - timedelta(days=7), today),
                    "Laatste 30 dagen": (today - timedelta(days=30), today),
                    "Laatste 90 dagen": (today - timedelta(days=90), today),
                    "Dit jaar": (date(today.year, 1, 1), today),
                    "Alle data": (min_date, max_date),
                    "Custom": None
                }
                
                selected_period = st.selectbox("Selecteer periode:", list(period_options.keys()))
                
                if selected_period == "Custom":
                    start_date = st.date_input("Start datum", value=min_date, min_value=min_date, max_value=max_date)
                    end_date = st.date_input("Eind datum", value=max_date, min_value=min_date, max_value=max_date)
                else:
                    start_date, end_date = period_options[selected_period]
                
                # Filter data
                period_df = filter_data_by_date(df, start_date, end_date)
                
                st.info(f"📊 **{len(period_df)}** vacatures in geselecteerde periode")
        
            # Main dashboard
            if len(period_df) > 0:
                # Key metrics voor geselecteerde periode
                st.header(f"🎯 Overzicht Periode: {start_date} tot {end_date}")
                
                total_period = len(period_df)
                vervuld_period = len(period_df[period_df['Status_Categorie'] == 'Vervuld'])
                actief_period = len(period_df[period_df['Status_Categorie'] == 'Actief'])
                gemiddelde_reacties = period_df['Aantal reacties'].mean()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Totaal Vacatures", total_period)
                
                with col2:
                    fill_rate = (vervuld_period / total_period * 100) if total_period > 0 else 0
                    st.metric("Fill Rate", f"{fill_rate:.1f}%")
                
                with col3:
                    st.metric("Actieve Vacatures", actief_period)
                
                with col4:
                    st.metric("Ø Reacties per Vacature", f"{gemiddelde_reacties:.1f}")
                
                # Actionable Insights
                st.header("🎯 Actionable Insights")
                insights = get_actionable_insights(df, period_df)
                
                if insights:
                    for insight in insights:
                        if insight['type'] == 'urgent':
                            st.markdown(f"""
                            <div class="action-item urgent-action">
                                <h4>{insight['title']}</h4>
                                <p><strong>Situatie:</strong> {insight['description']}</p>
                                <p><strong>🎯 Actie:</strong> {insight['action']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        elif insight['type'] == 'warning':
                            st.markdown(f"""
                            <div class="action-item">
                                <h4>{insight['title']}</h4>
                                <p><strong>Situatie:</strong> {insight['description']}</p>
                                <p><strong>🎯 Actie:</strong> {insight['action']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.success(f"**{insight['title']}** - {insight['description']}")
                            st.info(f"🎯 **Actie:** {insight['action']}")
                        
                        if 'data' in insight and not insight['data'].empty:
                            with st.expander(f"Details bekijken"):
                                st.dataframe(insight['data'], use_container_width=True)
                
                # Tabs voor verschillende analyses
                tab1, tab2, tab3, tab4 = st.tabs(["📈 Dagelijkse Activiteit", "🏆 Vacature Performance", "👥 Recruiter Focus", "🌐 Kanaal ROI"])
                
                with tab1:
                    st.subheader("Dagelijkse Vacature Activiteit")
                    daily_chart = create_daily_activity_chart(period_df, (start_date, end_date))
                    st.plotly_chart(daily_chart, use_container_width=True)
                    
                    # Nieuwe vs gesloten overzicht
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🆕 Nieuwe Vacatures")
                        nieuwe_vacatures = period_df[period_df['Datum aanmaak'].dt.date >= start_date].sort_values('Datum aanmaak', ascending=False)
                        if len(nieuwe_vacatures) > 0:
                            for _, row in nieuwe_vacatures.head(10).iterrows():
                                st.write(f"• **{row['Functie']}** ({row['Eigenaar']}) - {row['Datum aanmaak'].strftime('%d-%m-%Y')}")
                        else:
                            st.info("Geen nieuwe vacatures in deze periode")
                    
                    with col2:
                        st.subheader("✅ Vervulde Vacatures")
                        vervulde_vacatures = period_df[period_df['Status_Categorie'] == 'Vervuld'].sort_values('Datum aanmaak', ascending=False)
                        if len(vervulde_vacatures) > 0:
                            for _, row in vervulde_vacatures.head(10).iterrows():
                                st.write(f"• **{row['Functie']}** ({row['Eigenaar']}) - {row['Aantal reacties']} reacties")
                        else:
                            st.info("Geen vervulde vacatures in deze periode")
                
                with tab2:
                    st.subheader("🏆 Vacature Performance Analyse")
                    st.markdown("*Performance score gebaseerd op: tijd open, aantal reacties, en status*")
                    
                    performance_table = create_vacancy_performance_table(period_df)
                    
                    # Kleurcodering voor performance scores
                    def color_performance(val):
                        if val >= 80:
                            return 'background-color: #d4edda'
                        elif val >= 60:
                            return 'background-color: #fff3cd'
                        else:
                            return 'background-color: #f8d7da'
                    
                    styled_table = performance_table.style.applymap(color_performance, subset=['Performance Score'])
                    st.dataframe(styled_table, use_container_width=True, height=400)
                    
                    # Top en bottom performers
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("🥇 Top 5 Performers")
                        top_5 = performance_table.head(5)[['Functie', 'Performance Score', 'Factoren']]
                        st.dataframe(top_5, use_container_width=True)
                    
                    with col2:
                        st.subheader("⚠️ Aandacht Vereist")
                        bottom_5 = performance_table.tail(5)[['Functie', 'Performance Score', 'Factoren']]
                        st.dataframe(bottom_5, use_container_width=True)
                
                with tab3:
                    st.subheader("👥 Recruiter Focus Area")
                    
                    recruiter_stats = period_df.groupby('Eigenaar').agg({
                        'Functie': 'count',
                        'Status_Categorie': lambda x: (x == 'Vervuld').sum(),
                        'Aantal reacties': ['sum', 'mean'],
                        'Dagen_Sinds_Aanmaak': 'mean'
                    }).round(1)
                    
                    recruiter_stats.columns = ['Totaal_Vacatures', 'Vervuld', 'Totaal_Reacties', 'Gem_Reacties', 'Gem_Dagen_Open']
                    recruiter_stats['Fill_Rate'] = (recruiter_stats['Vervuld'] / recruiter_stats['Totaal_Vacatures'] * 100).round(1)
                    
                    # Sorteer op aantal vacatures
                    recruiter_stats = recruiter_stats.sort_values('Totaal_Vacatures', ascending=False)
                    
                    st.dataframe(recruiter_stats, use_container_width=True)
                    
                    # Recruiter vergelijking chart
                    if len(recruiter_stats) > 1:
                        fig = make_subplots(
                            rows=1, cols=2,
                            subplot_titles=('Aantal Vacatures', 'Fill Rate (%)'),
                            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
                        )
                        
                        fig.add_trace(
                            go.Bar(x=recruiter_stats.index, y=recruiter_stats['Totaal_Vacatures'], name='Vacatures'),
                            row=1, col=1
                        )
                        
                        fig.add_trace(
                            go.Bar(x=recruiter_stats.index, y=recruiter_stats['Fill_Rate'], name='Fill Rate'),
                            row=1, col=2
                        )
                        
                        fig.update_layout(height=400, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                
                with tab4:
                    st.subheader("🌐 Kanaal ROI & Optimalisatie")
                    
                    channels = ['V&VN', 'Indeed', 'Infopuntzorg', 'Zorgselect', 'Facebook', 'Linkedin', 'Twitter', 'Instagram']
                    channel_analysis = []
                    
                    for channel in channels:
                        total_col = f'Totaal per wervingskanaal: {channel}'
                        hired_col = f'Totaal per wervingskanaal (aangenomen): {channel}'
                        
                        if total_col in period_df.columns:
                            total = period_df[total_col].sum()
                            hired = period_df[hired_col].sum() if hired_col in period_df.columns else 0
                            
                            if total > 0:
                                conversion = (hired / total * 100)
                                channel_analysis.append({
                                    'Kanaal': channel,
                                    'Sollicitanten': total,
                                    'Aangenomen': hired,
                                    'Conversie (%)': round(conversion, 1),
                                    'Cost per Hire': "N/A",  # Kan later toegevoegd worden
                                    'Aanbeveling': 'Verhoog budget' if conversion > 10 else 'Optimaliseer targeting' if conversion > 5 else 'Evalueer effectiviteit'
                                })
                    
                    if channel_analysis:
                        channel_df = pd.DataFrame(channel_analysis).sort_values('Conversie (%)', ascending=False)
                        st.dataframe(channel_df, use_container_width=True)
                        
                        # Visualisatie
                        fig = px.scatter(
                            channel_df, 
                            x='Sollicitanten', 
                            y='Conversie (%)',
                            size='Aangenomen',
                            color='Kanaal',
                            title='Kanaal Performance: Volume vs Conversie',
                            hover_data=['Aanbeveling']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Geen kanaaldata beschikbaar voor analyse")
            
            else:
                st.warning("Geen data gevonden voor de geselecteerde periode.")
    
    else:
        # Landing page
        st.markdown("""
        ## 🚀 Actionable ATS Dashboard
        
        **Deze dashboard is ontworpen om concrete acties te ondersteunen:**
        
        ### 🎯 Wat maakt dit dashboard actionable:
        
        ✅ **Datum-gefocuste filtering** - Analyseer specifieke periodes  
        ✅ **Concrete actie-items** - Krijg specifieke aanbevelingen  
        ✅ **Performance scoring** - Identificeer probleem vacatures  
        ✅ **Recruiter focus** - Zie waar team ondersteuning nodig heeft  
        ✅ **ROI optimalisatie** - Optimaliseer kanaal spending  
        
        ### 📊 Voorbeelden van actionable insights:
        
        - **"5 vacatures staan >30 dagen open"** → Review job requirements
        - **"LinkedIn conversie <3%"** → Optimaliseer targeting of stop budget  
        - **"Recruiter X heeft 90% fill rate"** → Deel best practices met team
        - **"10 vacatures zonder reacties"** → Check visibility en job description
        
        ### 📁 Upload je CSV om te starten
        """)

if __name__ == "__main__":
    main()
