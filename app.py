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
        
        # Converteer datums
        date_columns = ['Datum aanmaak', 'Startdatum intern', 'Einddatum intern', 
                       'Startdatum extern', 'Einddatum extern']
        
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')
        
        # Vervang 0000-00-00 datums met NaT
        for col in date_columns:
            if col in df.columns:
                df[col] = df[col].replace('0000-00-00', pd.NaT)
        
        return df
    
    except Exception as e:
        st.error(f"Fout bij het laden van data: {str(e)}")
        return None

def calculate_metrics(df):
    """Berekent key metrics"""
    total_vacatures = len(df)
    vervulde_vacatures = len(df[df['Status vacature'].isin(['Extern vervuld', 'Intern vervuld'])])
    openstaande_vacatures = len(df[df['Status vacature'].isin(['Publicatie in- en extern', 'In procedure', 'Publicatie intern'])])
    niet_vervulde_vacatures = len(df[df['Status vacature'] == 'Niet vervuld'])
    
    fill_rate = (vervulde_vacatures / total_vacatures * 100) if total_vacatures > 0 else 0
    
    return {
        'total_vacatures': total_vacatures,
        'vervulde_vacatures': vervulde_vacatures,
        'openstaande_vacatures': openstaande_vacatures,
        'niet_vervulde_vacatures': niet_vervulde_vacatures,
        'fill_rate': fill_rate
    }

def create_status_chart(df):
    """Maakt status verdeling chart"""
    status_counts = df['Status vacature'].value_counts()
    
    # Kleurenschema
    colors = {
        'Extern vervuld': '#2ca02c',
        'Intern vervuld': '#17becf',
        'Niet vervuld': '#d62728',
        'Publicatie in- en extern': '#ff7f0e',
        'In procedure': '#ffbb78',
        'Ingetrokken': '#c7c7c7'
    }
    
    fig = px.pie(
        values=status_counts.values,
        names=status_counts.index,
        title="Verdeling Vacaturestatus",
        color=status_counts.index,
        color_discrete_map=colors
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_recruiter_performance_chart(df):
    """Maakt recruiter performance chart"""
    df_clean = df[df['Eigenaar'].notna() & (df['Eigenaar'] != ' ') & (df['Eigenaar'] != '')]
    
    recruiter_stats = df_clean.groupby('Eigenaar').agg({
        'Functie': 'count',
        'Aantal reacties': 'sum'
    }).rename(columns={'Functie': 'Totaal_Vacatures'})
    
    vervulde_per_recruiter = df_clean[df_clean['Status vacature'].isin(['Extern vervuld', 'Intern vervuld'])].groupby('Eigenaar').size()
    recruiter_stats['Vervulde_Vacatures'] = vervulde_per_recruiter.fillna(0)
    recruiter_stats['Fill_Rate'] = (recruiter_stats['Vervulde_Vacatures'] / recruiter_stats['Totaal_Vacatures'] * 100).round(1)
    recruiter_stats['Gem_Reacties'] = (recruiter_stats['Aantal reacties'] / recruiter_stats['Totaal_Vacatures']).round(1)
    
    recruiter_stats = recruiter_stats[recruiter_stats['Totaal_Vacatures'] >= 5].sort_values('Totaal_Vacatures', ascending=True)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Aantal Vacatures per Recruiter', 'Fill Rate per Recruiter'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    fig.add_trace(
        go.Bar(
            y=recruiter_stats.index,
            x=recruiter_stats['Totaal_Vacatures'],
            name='Totaal Vacatures',
            orientation='h',
            marker_color='lightblue'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            y=recruiter_stats.index,
            x=recruiter_stats['Fill_Rate'],
            name='Fill Rate (%)',
            orientation='h',
            marker_color='lightgreen'
        ),
        row=1, col=2
    )
    
    fig.update_layout(height=600, showlegend=False)
    fig.update_xaxes(title_text="Aantal Vacatures", row=1, col=1)
    fig.update_xaxes(title_text="Fill Rate (%)", row=1, col=2)
    
    return fig, recruiter_stats

def create_channel_analysis(df):
    """Analyseert wervingskanalen"""
    channels = ['V&VN', 'Indeed', 'Infopuntzorg', 'Zorgselect', 'Facebook', 
               'Linkedin', 'Twitter', 'Instagram', 'Via medewerker van SEIN', 'Anders']
    
    channel_data = []
    
    for channel in channels:
        total_col = f'Totaal per wervingskanaal: {channel}'
        hired_col = f'Totaal per wervingskanaal (aangenomen): {channel}'
        rejected_col = f'Totaal per wervingskanaal (afgewezen): {channel}'
        
        if total_col in df.columns:
            total = df[total_col].sum()
            hired = df[hired_col].sum() if hired_col in df.columns else 0
            rejected = df[rejected_col].sum() if rejected_col in df.columns else 0
            
            if total > 0:
                conversion_rate = (hired / total * 100)
                channel_data.append({
                    'Kanaal': channel,
                    'Totaal_Sollicitanten': total,
                    'Aangenomen': hired,
                    'Afgewezen': rejected,
                    'Conversie_Rate': conversion_rate
                })
    
    channel_df = pd.DataFrame(channel_data)
    channel_df = channel_df[channel_df['Totaal_Sollicitanten'] > 0].sort_values('Totaal_Sollicitanten', ascending=False)
    
    if len(channel_df) > 0:
        fig1 = px.bar(
            channel_df,
            x='Kanaal',
            y='Totaal_Sollicitanten',
            title='Aantal Sollicitanten per Kanaal',
            color='Totaal_Sollicitanten',
            color_continuous_scale='Blues'
        )
        fig1.update_xaxes(tickangle=45)
        
        fig2 = px.bar(
            channel_df,
            x='Kanaal',
            y='Conversie_Rate',
            title='Conversieratio per Kanaal (%)',
            color='Conversie_Rate',
            color_continuous_scale='Greens'
        )
        fig2.update_xaxes(tickangle=45)
        
        return fig1, fig2, channel_df
    
    return None, None, pd.DataFrame()

def create_timeline_analysis(df):
    """Maakt tijdlijn analyse"""
    if 'Datum aanmaak' not in df.columns:
        return None
    
    df_timeline = df.copy()
    df_timeline['Maand'] = df_timeline['Datum aanmaak'].dt.to_period('M')
    
    timeline_data = df_timeline.groupby('Maand').agg({
        'Functie': 'count',
        'Aantal reacties': 'sum'
    }).rename(columns={'Functie': 'Vacatures_Aangemaakt'})
    
    vervulde_timeline = df_timeline[df_timeline['Status vacature'].isin(['Extern vervuld', 'Intern vervuld'])].groupby('Maand').size()
    timeline_data['Vervulde_Vacatures'] = vervulde_timeline.fillna(0)
    
    if len(timeline_data) > 1:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[str(x) for x in timeline_data.index],
            y=timeline_data['Vacatures_Aangemaakt'],
            mode='lines+markers',
            name='Vacatures Aangemaakt',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=[str(x) for x in timeline_data.index],
            y=timeline_data['Vervulde_Vacatures'],
            mode='lines+markers',
            name='Vervulde Vacatures',
            line=dict(color='green')
        ))
        
        fig.update_layout(
            title='Vacatures over Tijd',
            xaxis_title='Maand',
            yaxis_title='Aantal Vacatures',
            height=400
        )
        
        return fig
    
    return None

def main():
    st.title("📊 ATS Recruitment Dashboard")
    st.markdown("Upload je ATS export CSV om uitgebreide recruitment analytics te bekijken")
    
    # Sidebar voor file upload + datumselectie
    with st.sidebar:
        st.header("📁 Data Upload")
        uploaded_file = st.file_uploader(
            "Upload je ATS CSV bestand",
            type=['csv'],
            help="Upload het CSV bestand geëxporteerd uit je ATS systeem"
        )
        st.success("✅ Bestand succesvol geladen!") if uploaded_file else None
        
        st.markdown("---")
        st.header("📆 Datum selectie")
        today = date.today()
        opties = [
            "Laatste 7 dagen",
            "Laatste 14 dagen",
            "Laatste 30 dagen",
            "Deze maand",
            "Aangepaste periode"
        ]
        keuze = st.selectbox("Selecteer periode", opties)
        
        if keuze == "Laatste 7 dagen":
            start_date = today - timedelta(days=7)
            end_date = today
        elif keuze == "Laatste 14 dagen":
            start_date = today - timedelta(days=14)
            end_date = today
        elif keuze == "Laatste 30 dagen":
            start_date = today - timedelta(days=30)
            end_date = today
        elif keuze == "Deze maand":
            start_date = today.replace(day=1)
            end_date = today
        else:  # Aangepaste periode
            start_date, end_date = st.date_input(
                "Kies datumbereik",
                value=[today - timedelta(days=7), today],
                help="Selecteer begin- en einddatum"
            )
        
        st.markdown(f"**Getoond:** {start_date.strftime('%d-%m-%Y')} tot {end_date.strftime('%d-%m-%Y')}")
    
    if uploaded_file is not None:
        # Laad data
        with st.spinner('Data aan het verwerken...'):
            df = load_and_process_data(uploaded_file)
        
        if df is not None:
            # **Hier de filtering toepassen**
            df = df.loc[
                (df['Datum aanmaak'] >= pd.to_datetime(start_date)) &
                (df['Datum aanmaak'] <= pd.to_datetime(end_date))
            ]
            
            # Key Metrics
            metrics = calculate_metrics(df)
            
            st.header("🎯 Key Performance Indicators")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Totaal Vacatures",
                    value=metrics['total_vacatures']
                )
            
            with col2:
                st.metric(
                    label="Vervulde Vacatures",
                    value=metrics['vervulde_vacatures']
                )
            
            with col3:
                st.metric(
                    label="Openstaande Vacatures",
                    value=metrics['openstaande_vacatures']
                )
            
            with col4:
                st.metric(
                    label="Fill Rate",
                    value=f"{metrics['fill_rate']:.1f}%"
                )
            
            # Charts in tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📈 Status Overzicht", "👥 Recruiter Performance", "🌐 Kanaal Analyse", "📅 Tijdlijn"])
            
            with tab1:
                st.header("Vacaturestatus Verdeling")
                status_fig = create_status_chart(df)
                st.plotly_chart(status_fig, use_container_width=True)
                
                st.subheader("Status Details")
                status_table = df['Status vacature'].value_counts().reset_index()
                status_table.columns = ['Status', 'Aantal']
                status_table['Percentage'] = (status_table['Aantal'] / len(df) * 100).round(1)
                st.dataframe(status_table, use_container_width=True)
            
            with tab2:
                st.header("Recruiter Performance")
                perf_fig, recruiter_stats = create_recruiter_performance_chart(df)
                st.plotly_chart(perf_fig, use_container_width=True)
                
                st.subheader("Recruiter Statistieken")
                recruiter_display = recruiter_stats.copy()
                recruiter_display.columns = ['Totaal Vacatures', 'Totaal Reacties', 'Vervulde Vacatures', 'Fill Rate (%)', 'Gem. Reacties']
                st.dataframe(recruiter_display, use_container_width=True)
            
            with tab3:
                st.header("Wervingskanaal Analyse")
                channel_fig1, channel_fig2, channel_df = create_channel_analysis(df)
                
                if channel_fig1 is not None:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.plotly_chart(channel_fig1, use_container_width=True)
                    with col2:
                        st.plotly_chart(channel_fig2, use_container_width=True)
                    
                    st.subheader("Kanaal Performance Tabel")
                    channel_display = channel_df.copy()
                    channel_display['Conversie_Rate'] = channel_display['Conversie_Rate'].round(1)
                    channel_display.columns = ['Kanaal', 'Totaal Sollicitanten', 'Aangenomen', 'Afgewezen', 'Conversie Rate (%)']
                    st.dataframe(channel_display, use_container_width=True)
                else:
                    st.info("Geen kanaaldata beschikbaar in de huidige export.")
            
            with tab4:
                st.header("Tijdlijn Analyse")
                timeline_fig = create_timeline_analysis(df)
                
                if timeline_fig is not None:
                    st.plotly_chart(timeline_fig, use_container_width=True)
                else:
                    st.info("Onvoldoende tijdsdata voor tijdlijn analyse (dataset lijkt recent te zijn).")
                
                st.subheader("Dataset Informatie")
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'Datum aanmaak' in df.columns:
                        min_date = df['Datum aanmaak'].min()
                        max_date = df['Datum aanmaak'].max()
                        st.write(f"**Datum bereik:** {min_date.strftime('%d-%m-%Y') if pd.notna(min_date) else 'Onbekend'} tot {max_date.strftime('%d-%m-%Y') if pd.notna(max_date) else 'Onbekend'}")
                
                with col2:
                    total_applicants = df['Aantal reacties'].sum()
                    st.write(f"**Totaal aantal reacties:** {total_applicants:,}")
            
            with st.expander("🔍 Bekijk ruwe data"):
                st.dataframe(df, use_container_width=True)
                
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 Download verwerkte data als CSV",
                    data=csv_data,
                    file_name="processed_ats_data.csv",
                    mime="text/csv"
                )
    else:
        # Landing page
        st.markdown("""
        ## 🚀 Welkom bij het ATS Recruitment Dashboard
        
        Deze applicatie helpt je om waardevolle inzichten te krijgen uit je ATS (Applicant Tracking System) export data.
        
        ### 📋 Wat kun je verwachten:
        
        ✅ **Vacaturestatus overzicht** - Zie welke vacatures vervuld, openstaand of niet vervuld zijn  
        ✅ **Recruiter performance** - Analyseer de prestaties van je recruiters  
        ✅ **Kanaal effectiviteit** - Ontdek welke wervingskanalen het beste werken  
        ✅ **Tijdlijn analyse** - Bekijk trends over tijd  
        
        ### 📁 Hoe te gebruiken:
        1. Upload je CSV export vanuit je ATS systeem via de sidebar
        2. Selecteer een datumbereik
        3. Het dashboard wordt automatisch gegenereerd
        
        ### 🔧 Ondersteunde formaten:
        - CSV bestanden met puntkomma (;) als delimiter
        - Multiple encodings (UTF-8, CP1252, etc.)
        
        **Upload je bestand om te beginnen! →**
        """)

if __name__ == "__main__":
    main()
