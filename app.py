import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta, date
import io
import html
import re

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
    .vacature-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def clean_html_entities(text):
    """Converteert HTML entities naar normale tekst"""
    if pd.isna(text) or not isinstance(text, str):
        return text
    
    # HTML entities decoderen
    text = html.unescape(text)
    
    # Extra cleanup voor veelvoorkomende encoding issues
    replacements = {
        '&ouml;': 'ö',
        '&euml;': 'ë', 
        '&uuml;': 'ü',
        '&auml;': 'ä',
        '&iuml;': 'ï',
        '&eacute;': 'é',
        '&egrave;': 'è',
        '&aacute;': 'á',
        '&agrave;': 'à',
        '&uacute;': 'ú',
        '&ugrave;': 'ù',
        '&oacute;': 'ó',
        '&ograve;': 'ò',
        '&iacute;': 'í',
        '&igrave;': 'ì',
        '&ccedil;': 'ç',
        '&ntilde;': 'ñ',
        '&amp;': '&',
        '&quot;': '"',
        '&lt;': '<',
        '&gt;': '>',
        '&nbsp;': ' '
    }
    
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    return text

def get_predefined_periods():
    """Definieert standaard periode opties"""
    today = date.today()
    
    periods = {
        "Laatste 7 dagen": (today - timedelta(days=7), today),
        "Laatste 14 dagen": (today - timedelta(days=14), today),
        "Laatste 30 dagen": (today - timedelta(days=30), today),
        "Laatste 90 dagen": (today - timedelta(days=90), today),
        "Huidige maand": (today.replace(day=1), today),
        "Vorige maand": get_previous_month_range(today),
        "Huidige kwartaal": get_current_quarter_range(today),
        "Huidige kalenderjaar": (date(today.year, 1, 1), today),
        "Laatste jaar": (today - timedelta(days=365), today),
        "Aangepast": None  # Voor custom date selection
    }
    
    return periods

def get_previous_month_range(current_date):
    """Berekent vorige maand periode"""
    if current_date.month == 1:
        start = date(current_date.year - 1, 12, 1)
        end = date(current_date.year, 1, 1) - timedelta(days=1)
    else:
        start = date(current_date.year, current_date.month - 1, 1)
        if current_date.month == 2:
            end = date(current_date.year, 2, 1) - timedelta(days=1)
        else:
            end = date(current_date.year, current_date.month, 1) - timedelta(days=1)
    return start, end

def get_current_quarter_range(current_date):
    """Berekent huidige kwartaal periode"""
    quarter = (current_date.month - 1) // 3 + 1
    start_month = 3 * (quarter - 1) + 1
    start = date(current_date.year, start_month, 1)
    return start, current_date
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
        
        # Status datum kolommen
        status_date_columns = [col for col in df.columns if col in [
            'Nieuw', 'Intake', 'Tekst bij vacaturehouder', 'Tekst akkoord', 
            'Publicatie intern', 'Publicatie in- en extern', 'In procedure',
            'Intern vervuld', 'Extern vervuld', 'Ingetrokken', 'Niet vervuld'
        ]]
        
        all_date_columns = date_columns + status_date_columns
        
        for col in all_date_columns:
            if col in df.columns:
                # Converteer verschillende datumformaten
                df[col] = pd.to_datetime(df[col], format='%d-%m-%Y', errors='coerce')
                # Vervang 0000-00-00 datums met NaT
                mask = df[col].dt.year == 1900
                df.loc[mask, col] = pd.NaT
        
        # Bepaal vervuldatum (wanneer vacature werd gesloten)
        df['Vervuldatum'] = df['Extern vervuld'].fillna(df['Intern vervuld'])
        df['Sluitdatum'] = df['Vervuldatum'].fillna(df['Niet vervuld']).fillna(df['Ingetrokken'])
        
        return df
    
    except Exception as e:
        st.error(f"Fout bij het laden van data: {str(e)}")
        return None

def get_date_range_from_data(df):
    """Bepaalt de datum range van de dataset"""
    date_columns = ['Datum aanmaak', 'Startdatum intern', 'Startdatum extern']
    all_dates = []
    
    for col in date_columns:
        if col in df.columns:
            valid_dates = df[col].dropna()
            all_dates.extend(valid_dates.tolist())
    
    if all_dates:
        min_date = min(all_dates).date()
        max_date = max(all_dates).date()
        return min_date, max_date
    
    return date.today() - timedelta(days=365), date.today()

def filter_data_by_date_range(df, start_date, end_date):
    """Filtert data op basis van geselecteerde datum range"""
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    
    # Filter op aanmaakdatum
    mask = (df['Datum aanmaak'] >= start_date) & (df['Datum aanmaak'] <= end_date)
    return df[mask].copy()

def calculate_metrics(df, start_date, end_date):
    """Berekent key metrics voor de geselecteerde periode"""
    total_vacatures = len(df)
    vervulde_vacatures = len(df[df['Status vacature'].isin(['Extern vervuld', 'Intern vervuld'])])
    openstaande_vacatures = len(df[df['Status vacature'].isin(['Publicatie in- en extern', 'In procedure', 'Publicatie intern'])])
    niet_vervulde_vacatures = len(df[df['Status vacature'] == 'Niet vervuld'])
    
    fill_rate = (vervulde_vacatures / total_vacatures * 100) if total_vacatures > 0 else 0
    
    # Nieuwe vacatures in periode
    periode_start = pd.Timestamp(start_date)
    periode_end = pd.Timestamp(end_date)
    nieuwe_vacatures = len(df[(df['Datum aanmaak'] >= periode_start) & (df['Datum aanmaak'] <= periode_end)])
    
    # Gesloten vacatures in periode (vervuld of niet vervuld)
    gesloten_in_periode = len(df[
        ((df['Vervuldatum'] >= periode_start) & (df['Vervuldatum'] <= periode_end)) |
        ((df['Niet vervuld'] >= periode_start) & (df['Niet vervuld'] <= periode_end)) |
        ((df['Ingetrokken'] >= periode_start) & (df['Ingetrokken'] <= periode_end))
    ])
    
    return {
        'total_vacatures': total_vacatures,
        'vervulde_vacatures': vervulde_vacatures,
        'openstaande_vacatures': openstaande_vacatures,
        'niet_vervulde_vacatures': niet_vervulde_vacatures,
        'fill_rate': fill_rate,
        'nieuwe_vacatures': nieuwe_vacatures,
        'gesloten_vacatures': gesloten_in_periode
    }

def create_daily_activity_chart(df, start_date, end_date):
    """Maakt dagelijkse activiteit chart"""
    periode_start = pd.Timestamp(start_date)
    periode_end = pd.Timestamp(end_date)
    
    # Maak datum range
    date_range = pd.date_range(start=periode_start, end=periode_end, freq='D')
    daily_data = pd.DataFrame({'Datum': date_range})
    
    # Tel nieuwe vacatures per dag
    nieuwe_per_dag = df.groupby(df['Datum aanmaak'].dt.date).size().reset_index()
    nieuwe_per_dag.columns = ['Datum', 'Nieuwe_Vacatures']
    nieuwe_per_dag['Datum'] = pd.to_datetime(nieuwe_per_dag['Datum'])
    
    # Tel gesloten vacatures per dag
    gesloten_data = []
    for _, row in df.iterrows():
        if pd.notna(row['Vervuldatum']):
            gesloten_data.append({'Datum': row['Vervuldatum'].date(), 'Type': 'Vervuld'})
        elif pd.notna(row['Niet vervuld']):
            gesloten_data.append({'Datum': row['Niet vervuld'].date(), 'Type': 'Niet vervuld'})
        elif pd.notna(row['Ingetrokken']):
            gesloten_data.append({'Datum': row['Ingetrokken'].date(), 'Type': 'Ingetrokken'})
    
    if gesloten_data:
        gesloten_df = pd.DataFrame(gesloten_data)
        gesloten_df['Datum'] = pd.to_datetime(gesloten_df['Datum'])
        gesloten_per_dag = gesloten_df.groupby('Datum').size().reset_index()
        gesloten_per_dag.columns = ['Datum', 'Gesloten_Vacatures']
    else:
        gesloten_per_dag = pd.DataFrame(columns=['Datum', 'Gesloten_Vacatures'])
    
    # Merge data
    daily_data = daily_data.merge(nieuwe_per_dag, on='Datum', how='left')
    daily_data = daily_data.merge(gesloten_per_dag, on='Datum', how='left')
    daily_data = daily_data.fillna(0)
    
    # Filter op periode
    daily_data = daily_data[(daily_data['Datum'] >= periode_start) & (daily_data['Datum'] <= periode_end)]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_data['Datum'],
        y=daily_data['Nieuwe_Vacatures'],
        mode='lines+markers',
        name='Nieuwe Vacatures',
        line=dict(color='blue'),
        fill='tonexty'
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['Datum'],
        y=daily_data['Gesloten_Vacatures'],
        mode='lines+markers',
        name='Gesloten Vacatures',
        line=dict(color='green'),
        fill='tonexty'
    ))
    
    fig.update_layout(
        title=f'Dagelijkse Vacature Activiteit ({start_date} - {end_date})',
        xaxis_title='Datum',
        yaxis_title='Aantal Vacatures',
        height=400,
        hovermode='x unified'
    )
    
    return fig

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

def create_vacature_performance_table(df):
    """Maakt gedetailleerde vacature performance tabel"""
    performance_data = []
    
    for _, row in df.iterrows():
        # Bereken doorlooptijd
        doorlooptijd = None
        if pd.notna(row['Sluitdatum']) and pd.notna(row['Datum aanmaak']):
            doorlooptijd = (row['Sluitdatum'] - row['Datum aanmaak']).days
        
        # Bepaal conversie rate
        totaal_reacties = row['Aantal reacties'] if pd.notna(row['Aantal reacties']) else 0
        aangenomen = 1 if row['Status vacature'] in ['Extern vervuld', 'Intern vervuld'] else 0
        conversie_rate = (aangenomen / totaal_reacties * 100) if totaal_reacties > 0 else 0
        
        # Bepaal status categorie
        status_categorie = 'Actief'
        if row['Status vacature'] in ['Extern vervuld', 'Intern vervuld']:
            status_categorie = 'Vervuld'
        elif row['Status vacature'] in ['Niet vervuld', 'Ingetrokken']:
            status_categorie = 'Gesloten'
        
        performance_data.append({
            'Vacature': row['Functie'][:50] + '...' if len(str(row['Functie'])) > 50 else row['Functie'],
            'Status': row['Status vacature'],
            'Status_Categorie': status_categorie,
            'Recruiter': row['Eigenaar'],
            'Aanmaakdatum': row['Datum aanmaak'].strftime('%d-%m-%Y') if pd.notna(row['Datum aanmaak']) else 'Onbekend',
            'Sluitdatum': row['Sluitdatum'].strftime('%d-%m-%Y') if pd.notna(row['Sluitdatum']) else '-',
            'Doorlooptijd': f"{doorlooptijd} dagen" if doorlooptijd is not None else '-',
            'Totaal_Reacties': int(totaal_reacties),
            'Conversie_Rate': f"{conversie_rate:.1f}%" if totaal_reacties > 0 else '-',
            'Locatie': row['Locatie'] if 'Locatie' in row and pd.notna(row['Locatie']) else 'Onbekend'
        })
    
    return pd.DataFrame(performance_data)

def create_recruiter_performance_chart(df):
    """Maakt recruiter performance chart"""
    # Filter alleen actieve recruiters
    df_clean = df[df['Eigenaar'].notna() & (df['Eigenaar'] != ' ') & (df['Eigenaar'] != '')]
    
    recruiter_stats = df_clean.groupby('Eigenaar').agg({
        'Functie': 'count',
        'Aantal reacties': 'sum'
    }).rename(columns={'Functie': 'Totaal_Vacatures'})
    
    # Bereken vervulde vacatures
    vervulde_per_recruiter = df_clean[df_clean['Status vacature'].isin(['Extern vervuld', 'Intern vervuld'])].groupby('Eigenaar').size()
    recruiter_stats['Vervulde_Vacatures'] = vervulde_per_recruiter.fillna(0)
    recruiter_stats['Fill_Rate'] = (recruiter_stats['Vervulde_Vacatures'] / recruiter_stats['Totaal_Vacatures'] * 100).round(1)
    recruiter_stats['Gem_Reacties'] = (recruiter_stats['Aantal reacties'] / recruiter_stats['Totaal_Vacatures']).round(1)
    
    # Filter recruiters met minimaal 3 vacatures voor relevantie
    recruiter_stats = recruiter_stats[recruiter_stats['Totaal_Vacatures'] >= 3].sort_values('Totaal_Vacatures', ascending=True)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Aantal Vacatures per Recruiter', 'Fill Rate per Recruiter'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Aantal vacatures
    fig.add_trace(
        go.Bar(
            y=recruiter_stats.index,
            x=recruiter_stats['Totaal_Vacatures'],
            name='Totaal Vacatures',
            orientation='h',
            marker_color='lightblue',
            text=recruiter_stats['Totaal_Vacatures'],
            textposition='auto'
        ),
        row=1, col=1
    )
    
    # Fill rate
    fig.add_trace(
        go.Bar(
            y=recruiter_stats.index,
            x=recruiter_stats['Fill_Rate'],
            name='Fill Rate (%)',
            orientation='h',
            marker_color='lightgreen',
            text=[f"{x:.1f}%" for x in recruiter_stats['Fill_Rate']],
            textposition='auto'
        ),
        row=1, col=2
    )
    
    fig.update_layout(height=max(400, len(recruiter_stats) * 30), showlegend=False)
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
        # Chart voor totaal sollicitanten
        fig1 = px.bar(
            channel_df,
            x='Kanaal',
            y='Totaal_Sollicitanten',
            title='Aantal Sollicitanten per Kanaal',
            color='Totaal_Sollicitanten',
            color_continuous_scale='Blues',
            text='Totaal_Sollicitanten'
        )
        fig1.update_traces(textposition='outside')
        fig1.update_xaxes(tickangle=45)
        
        # Chart voor conversie rates
        fig2 = px.bar(
            channel_df,
            x='Kanaal',
            y='Conversie_Rate',
            title='Conversieratio per Kanaal (%)',
            color='Conversie_Rate',
            color_continuous_scale='Greens',
            text=[f"{x:.1f}%" for x in channel_df['Conversie_Rate']]
        )
        fig2.update_traces(textposition='outside')
        fig2.update_xaxes(tickangle=45)
        
        return fig1, fig2, channel_df
    
    return None, None, pd.DataFrame()

def main():
    st.title("📊 ATS Recruitment Dashboard")
    st.markdown("Upload je ATS export CSV om uitgebreide recruitment analytics te bekijken")
    
    # Sidebar voor file upload en filters
    with st.sidebar:
        st.header("📁 Data Upload")
        uploaded_file = st.file_uploader(
            "Upload je ATS CSV bestand",
            type=['csv'],
            help="Upload het CSV bestand geëxporteerd uit je ATS systeem"
        )
        
        if uploaded_file:
            st.success("✅ Bestand succesvol geladen!")
            
            # Data info
            file_details = {
                "Bestandsnaam": uploaded_file.name,
                "Bestandsgrootte": f"{uploaded_file.size / 1024:.1f} KB"
            }
            st.json(file_details)
    
    if uploaded_file is not None:
        # Laad data
        with st.spinner('Data aan het verwerken...'):
            df_full = load_and_process_data(uploaded_file)
        
        if df_full is not None:
            # Datumfilter in sidebar
            with st.sidebar:
                st.header("📅 Periode Selectie")
                
                # Bepaal datum range van data
                min_date, max_date = get_date_range_from_data(df_full)
                
                # Standaard periode opties
                periods = get_predefined_periods()
                
                # Filter periods die binnen data range vallen
                available_periods = {}
                for name, period_range in periods.items():
                    if period_range is None:  # "Aangepast" optie
                        available_periods[name] = None
                    else:
                        period_start, period_end = period_range
                        # Check of periode overlapt met beschikbare data
                        if period_end >= min_date and period_start <= max_date:
                            # Adjust to data boundaries
                            adjusted_start = max(period_start, min_date)
                            adjusted_end = min(period_end, max_date)
                            available_periods[name] = (adjusted_start, adjusted_end)
                
                period_choice = st.selectbox(
                    "Kies periode",
                    options=list(available_periods.keys()),
                    index=0
                )
                
                # Datum selectors (alleen tonen als "Aangepast" gekozen)
                if period_choice == "Aangepast":
                    start_date = st.date_input(
                        "Startdatum",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date
                    )
                    
                    end_date = st.date_input(
                        "Einddatum", 
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date
                    )
                    
                    if start_date > end_date:
                        st.error("Startdatum moet voor einddatum liggen!")
                        return
                else:
                    # Gebruik voorgedefinieerde periode
                    if available_periods[period_choice]:
                        start_date, end_date = available_periods[period_choice]
                    else:
                        start_date, end_date = min_date, max_date
                
                st.info(f"**Geselecteerde periode:** {(end_date - start_date).days + 1} dagen")
                st.caption(f"{start_date.strftime('%d-%m-%Y')} tot {end_date.strftime('%d-%m-%Y')}")
            
            # Filter data op geselecteerde periode
            df = filter_data_by_date_range(df_full, start_date, end_date)
            
            if len(df) == 0:
                st.warning("Geen data beschikbaar voor de geselecteerde periode.")
                st.info("Probeer een andere periode of controleer je data.")
                return
            
            # Key Metrics
            metrics = calculate_metrics(df_full, start_date, end_date)  # Gebruik volledige dataset voor context
            
            st.header(f"🎯 KPIs voor Periode ({start_date} t/m {end_date})")
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.metric(
                    label="Vacatures in Dataset",
                    value=len(df)
                )
            
            with col2:
                st.metric(
                    label="Nieuwe Vacatures",
                    value=metrics['nieuwe_vacatures']
                )
                
            with col3:
                st.metric(
                    label="Gesloten Vacatures", 
                    value=metrics['gesloten_vacatures']
                )
            
            with col4:
                st.metric(
                    label="Vervulde Vacatures",
                    value=metrics['vervulde_vacatures']
                )
            
            with col5:
                st.metric(
                    label="Openstaande Vacatures",
                    value=metrics['openstaande_vacatures']
                )
            
            with col6:
                st.metric(
                    label="Fill Rate",
                    value=f"{metrics['fill_rate']:.1f}%"
                )
            
            # Dagelijkse activiteit chart
            st.header("📈 Dagelijkse Activiteit")
            daily_chart = create_daily_activity_chart(df_full, start_date, end_date)
            st.plotly_chart(daily_chart, use_container_width=True)
            
            # Charts in tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Status Overzicht", 
                "👥 Recruiter Performance", 
                "🌐 Kanaal Analyse", 
                "📋 Vacature Details"
            ])
            
            with tab1:
                st.header("Vacaturestatus Verdeling")
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    status_fig = create_status_chart(df)
                    st.plotly_chart(status_fig, use_container_width=True)
                
                with col2:
                    # Status tabel met aantallen
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
                if len(recruiter_stats) > 0:
                    recruiter_display = recruiter_stats.copy()
                    recruiter_display.columns = ['Totaal Vacatures', 'Totaal Reacties', 'Vervulde Vacatures', 'Fill Rate (%)', 'Gem. Reacties']
                    st.dataframe(recruiter_display, use_container_width=True)
                else:
                    st.info("Geen recruiter data beschikbaar voor de geselecteerde periode.")
            
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
                st.header("Vacature Performance Details")
                
                # Filter opties
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    status_filter = st.multiselect(
                        "Filter op Status",
                        options=df['Status vacature'].unique(),
                        default=df['Status vacature'].unique()
                    )
                
                with col2:
                    recruiter_filter = st.multiselect(
                        "Filter op Recruiter",
                        options=df['Eigenaar'].dropna().unique(),
                        default=df['Eigenaar'].dropna().unique()
                    )
                
                with col3:
                    min_reacties = st.number_input(
                        "Minimaal aantal reacties",
                        min_value=0,
                        value=0,
                        step=1
                    )
                
                # Filter data
                filtered_df = df[
                    (df['Status vacature'].isin(status_filter)) &
                    (df['Eigenaar'].isin(recruiter_filter)) &
                    (df['Aantal reacties'] >= min_reacties)
                ]
                
                # Performance tabel
                performance_table = create_vacature_performance_table(filtered_df)
                
                st.subheader(f"Vacature Performance ({len(performance_table)} vacatures)")
                
                # Sorteer opties
                sort_by = st.selectbox(
                    "Sorteer op",
                    options=['Aanmaakdatum', 'Totaal_Reacties', 'Doorlooptijd', 'Status'],
                    index=0
                )
                
                if sort_by == 'Doorlooptijd':
                    # Speciale behandeling voor doorlooptijd sorting
                    performance_table['Doorlooptijd_Dagen'] = performance_table['Doorlooptijd'].apply(
                        lambda x: int(x.split()[0]) if x != '-' and 'dagen' in str(x) else 0
                    )
                    performance_table = performance_table.sort_values('Doorlooptijd_Dagen', ascending=False)
                    performance_table = performance_table.drop('Doorlooptijd_Dagen', axis=1)
                else:
                    performance_table = performance_table.sort_values(sort_by, ascending=False)
                
                # Toon tabel
                st.dataframe(
                    performance_table,
                    use_container_width=True,
                    column_config={
                        "Vacature": st.column_config.TextColumn("Vacature", width="large"),
                        "Status": st.column_config.TextColumn("Status", width="medium"),
                        "Recruiter": st.column_config.TextColumn("Recruiter", width="medium"),
                        "Totaal_Reacties": st.column_config.NumberColumn("Reacties", format="%d"),
                        "Conversie_Rate": st.column_config.TextColumn("Conversie"),
                    }
                )
                
                # Performance insights
                if len(performance_table) > 0:
                    st.subheader("📊 Performance Insights")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Top performer
                        top_conversie = performance_table[performance_table['Conversie_Rate'] != '-']
                        if len(top_conversie) > 0:
                            top_conversie['Conv_Numeric'] = top_conversie['Conversie_Rate'].str.replace('%', '').astype(float)
                            beste_conversie = top_conversie.loc[top_conversie['Conv_Numeric'].idxmax()]
                            st.success(f"**Beste Conversie:** {beste_conversie['Vacature'][:30]}... ({beste_conversie['Conversie_Rate']})")
                    
                    with col2:
                        # Meeste reacties
                        meeste_reacties = performance_table.loc[performance_table['Totaal_Reacties'].idxmax()]
                        st.info(f"**Meeste Reacties:** {meeste_reacties['Vacature'][:30]}... ({meeste_reacties['Totaal_Reacties']} reacties)")
                    
                    with col3:
                        # Snelste vervulling
                        vervulde_met_tijd = performance_table[
                            (performance_table['Status_Categorie'] == 'Vervuld') & 
                            (performance_table['Doorlooptijd'] != '-')
                        ]
                        if len(vervulde_met_tijd) > 0:
                            vervulde_met_tijd['Doorlooptijd_Dagen'] = vervulde_met_tijd['Doorlooptijd'].apply(
                                lambda x: int(x.split()[0]) if 'dagen' in str(x) else 999
                            )
                            snelste = vervulde_met_tijd.loc[vervulde_met_tijd['Doorlooptijd_Dagen'].idxmin()]
                            st.success(f"**Snelste Vervulling:** {snelste['Vacature'][:30]}... ({snelste['Doorlooptijd']})")
            
            # Uitgebreide Analytics Sectie
            st.header("📊 Uitgebreide Analytics")
            
            # Controleer welke inzichten we kunnen tonen
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Beschikbare Analyses")
                
                # Vacaturestatistieken
                st.write("✅ **Vacaturestatistieken**")
                st.write(f"• Openstaande rollen: {metrics['openstaande_vacatures']}")
                st.write(f"• Gesloten rollen: {metrics['vervulde_vacatures'] + metrics['niet_vervulde_vacatures']}")
                st.write(f"• Fill rate: {metrics['fill_rate']:.1f}%")
                st.write(f"• Actieve vacatures per recruiter: ✅ (zie Recruiter tab)")
                
                # Kanaalanalyse 
                channel_df = create_channel_analysis(df)[2]
                st.write("✅ **Kanaalanalyse**")
                if len(channel_df) > 0:
                    st.write(f"• Aantal actieve kanalen: {len(channel_df)}")
                    best_channel = channel_df.loc[channel_df['Conversie_Rate'].idxmax()]
                    st.write(f"• Beste kanaal: {best_channel['Kanaal']} ({best_channel['Conversie_Rate']:.1f}%)")
                    st.write(f"• Totaal sollicitanten: {channel_df['Totaal_Sollicitanten'].sum():,}")
                else:
                    st.write("• Geen kanaaldata beschikbaar")
                
                # Recruiter Performance
                st.write("✅ **Recruiter Performance**")
                recruiter_stats = create_recruiter_performance_chart(df)[1]
                if len(recruiter_stats) > 0:
                    top_recruiter = recruiter_stats.sort_values('Fill_Rate', ascending=False).iloc[0]
                    st.write(f"• Actieve recruiters: {len(recruiter_stats)}")
                    st.write(f"• Beste fill rate: {top_recruiter.name} ({top_recruiter['Fill_Rate']:.1f}%)")
                    st.write(f"• Totaal reacties: {recruiter_stats['Aantal reacties'].sum():,}")
            
            with col2:
                st.subheader("⚠️ Beperkte Analyses")
                
                # Tijdlijn analyses
                st.write("⚠️ **Tijdlijn Analyses**")
                period_days = (end_date - start_date).days
                if period_days < 30:
                    st.write("• Beperkte periode voor trends")
                elif period_days < 90:
                    st.write("• Korte periode - trends zichtbaar")
                else:
                    st.write("• Voldoende periode voor trend analyse")
                
                # Doorlooptijd analyses
                st.write("⚠️ **Doorlooptijd Analyses**")
                performance_table = create_vacature_performance_table(df)
                doorlooptijden = performance_table[performance_table['Doorlooptijd'] != '-']
                if len(doorlooptijden) > 0:
                    st.write(f"• Vacatures met doorlooptijd: {len(doorlooptijden)}")
                    st.write("• Gemiddelde doorlooptijd berekening mogelijk")
                else:
                    st.write("• Onvoldoende sluitdatums voor doorlooptijd")
                
                st.write("❌ **Niet Beschikbaar**")
                st.write("• Candidate journey tracking")
                st.write("• Funnel analyses (bezoekers → sollicitaties)")
                st.write("• Kosten per kanaal")
                st.write("• Time-to-reject specifiek")
                st.write("• Procesfase tijdsduur")
            
            # Summary van data completeness
            st.subheader("📋 Data Completeness Rapport")
            
            # Bereken data completeness scores
            completeness_scores = {}
            
            # Basis data
            completeness_scores['Basis Vacature Info'] = 100  # Altijd beschikbaar
            
            # Status data
            status_complete = (df['Status vacature'].notna().sum() / len(df)) * 100
            completeness_scores['Status Informatie'] = status_complete
            
            # Datum data  
            date_complete = (df['Datum aanmaak'].notna().sum() / len(df)) * 100
            completeness_scores['Datum Informatie'] = date_complete
            
            # Recruiter data
            recruiter_complete = (df['Eigenaar'].notna().sum() / len(df)) * 100
            completeness_scores['Recruiter Informatie'] = recruiter_complete
            
            # Reactie data
            reactie_complete = ((df['Aantal reacties'] > 0).sum() / len(df)) * 100
            completeness_scores['Sollicitatie Data'] = reactie_complete
            
            # Kanaal data
            kanaal_cols = [col for col in df.columns if 'wervingskanaal' in col and not col.endswith(('aangenomen)', 'afgewezen)'))]
            if kanaal_cols:
                kanaal_data = df[kanaal_cols].sum(axis=1) > 0
                kanaal_complete = (kanaal_data.sum() / len(df)) * 100
                completeness_scores['Kanaal Data'] = kanaal_complete
            else:
                completeness_scores['Kanaal Data'] = 0
            
            # Toon completeness scores
            completeness_df = pd.DataFrame(list(completeness_scores.items()), 
                                         columns=['Data Categorie', 'Completeness %'])
            completeness_df['Completeness %'] = completeness_df['Completeness %'].round(1)
            completeness_df['Status'] = completeness_df['Completeness %'].apply(
                lambda x: '🟢 Excellent' if x >= 90 else '🟡 Good' if x >= 70 else '🔴 Limited'
            )
            
            st.dataframe(completeness_df, use_container_width=True)
            
            # Gemiddelde completeness
            avg_completeness = completeness_df['Completeness %'].mean()
            
            if avg_completeness >= 85:
                st.success(f"🎉 **Uitstekende data kwaliteit!** Gemiddelde completeness: {avg_completeness:.1f}%")
                st.info("Je kunt alle beschikbare analyses gebruiken voor betrouwbare inzichten.")
            elif avg_completeness >= 70:
                st.warning(f"⚠️ **Goede data kwaliteit.** Gemiddelde completeness: {avg_completeness:.1f}%")
                st.info("De meeste analyses zijn betrouwbaar, maar sommige kunnen beperkt zijn.")
            else:
                st.error(f"🔴 **Beperkte data kwaliteit.** Gemiddelde completeness: {avg_completeness:.1f}%")
                st.info("Overweeg een meer complete data export voor betere inzichten.")
            
            # Download opties
            with st.expander("📥 Export Opties"):
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📊 Download Performance Rapport"):
                        performance_table = create_vacature_performance_table(df)
                        csv_buffer = io.StringIO()
                        performance_table.to_csv(csv_buffer, index=False, sep=';')
                        csv_data = csv_buffer.getvalue()
                        
                        st.download_button(
                            label="💾 Download Performance CSV",
                            data=csv_data,
                            file_name=f"vacature_performance_{start_date}_{end_date}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if st.button("📈 Download Gefilterde Data"):
                        csv_buffer = io.StringIO()
                        df.to_csv(csv_buffer, index=False, sep=';')
                        csv_data = csv_buffer.getvalue()
                        
                        st.download_button(
                            label="💾 Download Gefilterde CSV",
                            data=csv_data,
                            file_name=f"ats_data_filtered_{start_date}_{end_date}.csv",
                            mime="text/csv"
                        )
                        st.metric("Gesloten in Periode", len(closed_in_period))
    
    else:
        # Landing page
        st.markdown("""
        ## 🚀 Welkom bij het ATS Recruitment Dashboard
        
        Deze applicatie helpt je om waardevolle inzichten te krijgen uit je ATS (Applicant Tracking System) export data.
        
        ### 📋 Nieuwe Features:
        
        🗓️ **Slimme Periode Selectie** - Kies uit standaard periodes of maak aangepaste selecties  
        📈 **Dagelijkse Activiteit** - Zie nieuwe en gesloten vacatures per dag  
        📋 **Vacature Details** - Gedetailleerde performance per individuele vacature  
        📊 **Uitgebreide Analytics** - Volledig overzicht van beschikbare inzichten  
        🧹 **Automatische Data Cleaning** - HTML entities worden automatisch geconverteerd  
        
        ### 📊 Dashboard Functionaliteiten:
        
        ✅ **Status Overzicht** - Pie charts en KPIs voor vacaturestatus  
        ✅ **Recruiter Performance** - Vergelijk prestaties tussen recruiters  
        ✅ **Kanaal Analyse** - Ontdek welke wervingskanalen het beste werken  
        ✅ **Vacature Breakdown** - Performance metrics per individuele vacature  
        ✅ **Data Completeness Rapport** - Zie de kwaliteit van je data  
        
        ### 🗓️ Periode Opties:
        - **Laatste 7, 14, 30, 90 dagen** - Recente activiteit
        - **Huidige/vorige maand** - Maandelijkse analyses  
        - **Huidige kwartaal** - Kwartaal rapportage
        - **Kalenderjaar** - Jaarlijkse trends
        - **Aangepast** - Kies je eigen periode
        
        ### 📁 Hoe te gebruiken:
        1. **Upload** je CSV export vanuit je ATS systeem via de sidebar
        2. **Selecteer** een standaard periode of kies "Aangepast" voor specifieke datums
        3. **Navigeer** door de verschillende tabs voor verschillende analyses
        4. **Bekijk** de Uitgebreide Analytics voor een volledig overzicht
        5. **Export** rapporten voor verdere analyse
        
        ### 🔧 Ondersteunde formaten:
        - CSV bestanden met puntkomma (;) als delimiter
        - Multiple encodings (UTF-8, CP1252, etc.)
        - Datum formaten: DD-MM-YYYY
        - **Automatische HTML entity cleaning** (bijv. Co&ouml;rdinator → Coördinator)
        
        ### 💡 Pro Tips:
        - Begin met **"Laatste 30 dagen"** voor een snel overzicht
        - Gebruik **"Huidige kwartaal"** voor management rapportage
        - Check de **Uitgebreide Analytics** voor data completeness
        - **Export** performance rapporten voor presentaties
        - Vergelijk verschillende periodes voor trend analyse
        
        ### 📊 Beschikbare Inzichten:
        
        **✅ Volledig Ondersteund:**
        - Vacaturestatus verdelingen en trends
        - Fill rates per recruiter en overall  
        - Kanaal performance en conversie ratio's
        - Dagelijkse activiteit tracking
        - Individuele vacature performance
        - Doorlooptijd analyses (waar data beschikbaar)
        
        **⚠️ Beperkt Ondersteund:**
        - Tijdlijn trends (afhankelijk van periode lengte)
        - Procesfase analyses (afhankelijk van status data)
        
        **❌ Niet Ondersteund:**
        - Kandidaat journey tracking (vereist kandidaat-level data)
        - Funnel analyses (vereist web analytics)
        - Kosten analyses (niet in standaard export)
        
        **Upload je bestand om te beginnen! →**
        """)
        
        # Voorbeeld data structure
        with st.expander("📋 Verwachte Data Structuur"):
            st.markdown("""
            **Verplichte kolommen:**
            - `Functie` - Vacaturetitel
            - `Status vacature` - Huidige status
            - `Eigenaar` - Recruiter
            - `Datum aanmaak` - Aanmaakdatum vacature
            - `Aantal reacties` - Aantal sollicitaties
            
            **Optionele kolommen voor uitgebreide analyse:**
            - `Extern vervuld`, `Intern vervuld` - Vervuldatums voor doorlooptijd
            - `Niet vervuld`, `Ingetrokken` - Sluitdatums voor completeness
            - `Totaal per wervingskanaal: [KANAAL]` - Voor kanaal effectiviteit
            - `Totaal per wervingskanaal (aangenomen): [KANAAL]` - Voor conversie rates
            - `Locatie` - Voor geografische analyses
            
            **Automatische Cleaning:**
            - HTML entities worden automatisch geconverteerd
            - Datums in DD-MM-YYYY formaat worden herkend
            - Lege waarden en 0000-00-00 datums worden gefilterd
            """)

if __name__ == "__main__":
    main()
    
    else:
        # Landing page
        st.markdown("""
        ## 🚀 Welkom bij het ATS Recruitment Dashboard
        
        Deze applicatie helpt je om waardevolle inzichten te krijgen uit je ATS (Applicant Tracking System) export data.
        
        ### 📋 Nieuwe Features:
        
        🗓️ **Periode Selectie** - Kies specifieke datumbereiken voor analyse  
        📈 **Dagelijkse Activiteit** - Zie nieuwe en gesloten vacatures per dag  
        📋 **Vacature Details** - Gedetailleerde performance per individuele vacature  
        🔍 **Data Explorer** - Verken en exporteer je data  
        📊 **Performance Insights** - Automatische identificatie van top performers  
        
        ### 📊 Dashboard Functionaliteiten:
        
        ✅ **Status Overzicht** - Pie charts en KPIs voor vacaturestatus  
        ✅ **Recruiter Performance** - Vergelijk prestaties tussen recruiters  
        ✅ **Kanaal Analyse** - Ontdek welke wervingskanalen het beste werken  
        ✅ **Tijdlijn Analyse** - Bekijk trends en activiteit over tijd  
        ✅ **Vacature Breakdown** - Performance metrics per individuele vacature  
        
        ### 📁 Hoe te gebruiken:
        1. **Upload** je CSV export vanuit je ATS systeem via de sidebar
        2. **Selecteer** de gewenste analyseperiode met de datumfilters
        3. **Navigeer** door de verschillende tabs voor verschillende analyses
        4. **Export** gefilterde data of performance rapporten
        
        ### 🔧 Ondersteunde formaten:
        - CSV bestanden met puntkomma (;) als delimiter
        - Multiple encodings (UTF-8, CP1252, etc.)
        - Datum formaten: DD-MM-YYYY
        
        ### 💡 Pro Tips:
        - Start met een **korte periode** (1-3 maanden) voor gedetailleerde analyse
        - Gebruik **Vacature Details** tab voor individuele performance tracking
        - **Export** rapporten voor verdere analyse in Excel
        - Combineer **Status** en **Periode** filters voor specifieke inzichten
        
        **Upload je bestand om te beginnen! →**
        """)
        
        # Voorbeeld data structure
        with st.expander("📋 Verwachte Data Structuur"):
            st.markdown("""
            **Verplichte kolommen:**
            - `Functie` - Vacaturetitel
            - `Status vacature` - Huidige status
            - `Eigenaar` - Recruiter
            - `Datum aanmaak` - Aanmaakdatum vacature
            - `Aantal reacties` - Aantal sollicitaties
            
            **Optionele kolommen voor uitgebreide analyse:**
            - `Extern vervuld`, `Intern vervuld` - Vervuldatums
            - `Niet vervuld`, `Ingetrokken` - Sluitdatums
            - `Totaal per wervingskanaal: [KANAAL]` - Kanaal data
            - `Locatie` - Vestiging/locatie
            """)

if __name__ == "__main__":
    main()
