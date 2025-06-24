import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, date
import io

# Universele lijsten
FILLED_STATUSES = ['Extern vervuld', 'Intern vervuld']
CHANNELS = [
    'V&VN', 'Indeed', 'Infopuntzorg', 'Zorgselect', 'Facebook',
    'Linkedin', 'Twitter', 'Instagram', 'Via medewerker van SEIN', 'Anders'
]

def load_and_process_data(uploaded_file):
    try:
        encodings = ['utf-8','cp1252','iso-8859-1','latin-1']
        df = None
        for enc in encodings:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=enc, delimiter=';')
                break
            except UnicodeDecodeError:
                continue
        if df is None:
            st.error("Kon bestand niet inlezen. Controleer de encoding.")
            return None

        df.columns = df.columns.str.strip()
        date_cols = ['Datum aanmaak','Startdatum intern','Einddatum intern',
                     'Startdatum extern','Einddatum extern']
        for c in date_cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], format='%d-%m-%Y', errors='coerce')
                df[c] = df[c].replace('0000-00-00', pd.NaT)
        return df
    except Exception as e:
        st.error(f"Fout bij laden data: {e}")
        return None

def calculate_metrics(df):
    total = len(df)
    vervuld = df['Status vacature'].isin(FILLED_STATUSES).sum()
    openst = total - vervuld
    niet = (df['Status vacature']=='Niet vervuld').sum()
    fill = (vervuld/total*100) if total>0 else 0
    return {
        'total_vacatures': total,
        'vervulde_vacatures': vervuld,
        'openstaande_vacatures': openst,
        'niet_vervulde_vacatures': niet,
        'fill_rate': fill
    }

def create_status_chart(df):
    counts = df['Status vacature'].value_counts()
    colors = {
        'Extern vervuld':'#1f77b4','Intern vervuld':'#2ca02c','Niet vervuld':'#d62728',
        'Publicatie in- en extern':'#ff7f0e','In procedure':'#9467bd','Ingetrokken':'#8c564b'
    }
    fig = px.pie(
        values=counts.values, names=counts.index,
        title="Verdeling Vacaturestatus", color=counts.index,
        color_discrete_map=colors
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    return fig

def create_recruiter_performance_chart(df):
    dfc = df[df['Eigenaar'].notna() & (df['Eigenaar'].str.strip()!='')]
    stats = dfc.groupby('Eigenaar').agg({
        'Functie':'count','Aantal reacties':'sum'
    }).rename(columns={'Functie':'Totaal_Vacatures'})
    filled = dfc[dfc['Status vacature'].isin(FILLED_STATUSES)].groupby('Eigenaar').size()
    stats['Vervulde_Vacatures'] = filled.fillna(0)
    stats['Fill_Rate'] = (stats['Vervulde_Vacatures']/stats['Totaal_Vacatures']*100).round(1)
    stats['Gem_Reacties'] = (stats['Aantal reacties']/stats['Totaal_Vacatures']).round(1)
    stats = stats.sort_values('Totaal_Vacatures')
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Aantal Vacatures per Recruiter','Fill Rate per Recruiter'),
        specs=[[{}, {}]]
    )
    fig.add_trace(
        go.Bar(
            y=stats.index, x=stats['Totaal_Vacatures'],
            orientation='h', name='Vacatures'
        ), row=1, col=1
    )
    fig.add_trace(
        go.Bar(
            y=stats.index, x=stats['Fill_Rate'],
            orientation='h', name='Fill Rate (%)'
        ), row=1, col=2
    )
    fig.update_layout(height=600, showlegend=False)
    fig.update_xaxes(title_text="Aantal Vacatures", row=1,col=1)
    fig.update_xaxes(title_text="Fill Rate (%)", row=1,col=2)
    return fig, stats

def create_channel_analysis(df):
    data=[]
    for ch in CHANNELS:
        tot = f'Totaal per wervingskanaal: {ch}'
        hired = f'Totaal per wervingskanaal (aangenomen): {ch}'
        if tot in df.columns:
            t=df[tot].sum()
            h=df[hired].sum() if hired in df.columns else 0
            if t>0:
                data.append({'Kanaal':ch,'Totaal_Sollicitanten':t,'Conversie_Rate':h/t*100})
    cdf=pd.DataFrame(data).sort_values('Totaal_Sollicitanten',ascending=False)
    if cdf.empty: return None,None,cdf
    fig1=px.bar(cdf,x='Kanaal',y='Totaal_Sollicitanten',title='Aantal Sollicitanten per Kanaal',color='Totaal_Sollicitanten')
    fig1.update_xaxes(tickangle=45)
    fig2=px.bar(cdf,x='Kanaal',y='Conversie_Rate',title='Conversieratio per Kanaal (%)',color='Conversie_Rate')
    fig2.update_xaxes(tickangle=45)
    return fig1,fig2,cdf

def create_timeline_analysis(df):
    df2 = df.copy()
    df2['Datum'] = df2['Datum aanmaak'].dt.date
    grp = df2.groupby('Datum').agg({
        'Functie':'count','Aantal reacties':'sum'
    }).rename(columns={'Functie':'Vacatures_Aangemaakt'})
    filled = df2[df2['Status vacature'].isin(FILLED_STATUSES)].groupby('Datum').size()
    grp['Vervulde_Vacatures'] = filled.fillna(0)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grp.index, y=grp['Vacatures_Aangemaakt'],
        mode='lines+markers', name='Aangemaakt'
    ))
    fig.add_trace(go.Scatter(
        x=grp.index, y=grp['Vervulde_Vacatures'],
        mode='lines+markers', name='Vervuld'
    ))
    fig.update_layout(
        title='Vacatures over Tijd (per dag)',
        xaxis_title='Datum', yaxis_title='Aantal Vacatures',
        height=400
    )
    return fig

def main():
    st.set_page_config(page_title="ATS Recruitment Dashboard", page_icon="📊", layout="wide")
    st.title("📊 ATS Recruitment Dashboard")
    st.markdown("Upload je ATS export CSV en selecteer een datumbereik")

    # Sidebar: upload + datumselectie
    with st.sidebar:
        st.header("📁 Data Upload")
        uploaded_file = st.file_uploader("Upload je ATS CSV bestand", type=['csv'])
        if uploaded_file:
            st.success("✅ Bestand succesvol geladen!")
        st.markdown("---")
        st.header("📆 Datum selectie")
        today = date.today()
        opties = ["Laatste 7 dagen","Laatste 14 dagen","Laatste 30 dagen","Deze maand","Aangepaste periode"]
        keuze = st.selectbox("Selecteer periode", opties)
        if keuze=="Laatste 7 dagen":
            start_date, end_date = today-timedelta(days=7), today
        elif keuze=="Laatste 14 dagen":
            start_date, end_date = today-timedelta(days=14), today
        elif keuze=="Laatste 30 dagen":
            start_date, end_date = today-timedelta(days=30), today
        elif keuze=="Deze maand":
            start_date, end_date = today.replace(day=1), today
        else:
            start_date, end_date = st.date_input("Kies datumbereik", [today-timedelta(days=7),today])
        st.markdown(f"**Getoond:** {start_date.strftime('%d-%m-%Y')} tot {end_date.strftime('%d-%m-%Y')}")

    if not uploaded_file:
        st.info("Upload een bestand om te starten.")
        return

    df = load_and_process_data(uploaded_file)
    if df is None:
        return
    df = df.loc[
        (df['Datum aanmaak']>=pd.to_datetime(start_date)) &
        (df['Datum aanmaak']<=pd.to_datetime(end_date))
    ]

    # KPI's
    metrics = calculate_metrics(df)
    st.header("🎯 Key Performance Indicators")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Totaal Vacatures",metrics['total_vacatures'])
    c2.metric("Vervulde Vacatures",metrics['vervulde_vacatures'])
    c3.metric("Openstaande Vacatures",metrics['openstaande_vacatures'])
    c4.metric("Fill Rate",f"{metrics['fill_rate']:.1f}%")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Status Overzicht","👥 Recruiter Performance",
        "🌐 Kanaal Analyse","📅 Tijdlijn"
    ])

    with tab1:
        st.header("Vacaturestatus Verdeling")
        st.plotly_chart(create_status_chart(df), use_container_width=True)

    with tab2:
        st.header("Recruiter Performance")
        perf_fig, rec_stats = create_recruiter_performance_chart(df)
        st.plotly_chart(perf_fig, use_container_width=True)
        st.subheader("Details per Recruiter")
        recruiter = st.selectbox("Selecteer recruiter", rec_stats.index)
        df_rec = df[df['Eigenaar']==recruiter].copy()
        df_open = df_rec[~df_rec['Status vacature'].isin(FILLED_STATUSES)]
        df_open['Nieuw geopend'] = df_open['Datum aanmaak'].between(start_date, end_date)
        def top_ch(r):
            vals = {ch: r.get(f'Totaal per wervingskanaal: {ch}',0) for ch in CHANNELS}
            return max(vals, key=vals.get) if vals else None
        df_open['Top Kanaal'] = df_open.apply(top_ch, axis=1)
        st.dataframe(
            df_open[['Functie','Nieuw geopend','Aantal reacties','Top Kanaal']],
            use_container_width=True
        )

    with tab3:
        st.header("Wervingskanaal Analyse")
        fig1, fig2, cdf = create_channel_analysis(df)
        if fig1:
            col1,col2 = st.columns(2)
            col1.plotly_chart(fig1, use_container_width=True)
            col2.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Geen kanaaldata beschikbaar.")

    with tab4:
        st.header("Tijdlijn Analyse")
        st.plotly_chart(create_timeline_analysis(df), use_container_width=True)

if __name__=="__main__":
    main()
    
