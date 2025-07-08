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
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Status Overzicht", 
                "👥 Recruitment Performance", 
                "🌐 Kanaal Analyse", 
                "📋 Vacature Details",
                "🏢 Afdeling Analyse"
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
                st.header("Recruitment Performance (inclusief Afdeling)")
                perf_fig, recruiter_stats = create_recruitment_performance_chart(df)
                st.plotly_chart(perf_fig, use_container_width=True)
                
                st.subheader("Recruitment Team Statistieken")
                if len(recruiter_stats) > 0:
                    recruiter_display = recruiter_stats[['Eigenaar', 'Afdeling', 'Totaal_Vacatures', 'Aantal reacties', 'Vervulde_Vacatures', 'Fill_Rate', 'Gem_Reacties']].copy()
                    recruiter_display.columns = ['Recruiter', 'Afdeling', 'Totaal Vacatures', 'Totaal Reacties', 'Vervulde Vacatures', 'Fill Rate (%)', 'Gem. Reacties']
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
                st.header("Gedetailleerde Vacature Performance")
                
                # Filter opties
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    status_filter = st.multiselect(
                        "Filter op Status",
                        options=df['Status vacature'].unique(),
                        default=df['Status vacature'].unique()
                    )
                
                with col2:
                    if 'Afdeling' in df.columns:
                        afdeling_filter = st.multiselect(
                            "Filter op Afdeling",
                            options=df['Afdeling'].dropna().unique(),
                            default=df['Afdeling'].dropna().unique()
                        )
                    else:
                        afdeling_filter = []
                
                with col3:
                    min_kandidaten = st.number_input(
                        "Minimaal aantal kandidaten",
                        min_value=0,
                        value=0,
                        step=1
                    )
                
                # Filter data
                filtered_df = df[df['Status vacature'].isin(status_filter)]
                if afdeling_filter and 'Afdeling' in df.columns:
                    filtered_df = filtered_df[filtered_df['Afdeling'].isin(afdeling_filter)]
                if 'Aantal reacties' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['Aantal reacties'] >= min_kandidaten]
                
                # Gedetailleerde analyse tabel
                detailed_analysis = create_detailed_vacature_analysis(filtered_df)
                
                st.subheader(f"Vacature Performance Analyse ({len(detailed_analysis)} vacatures)")
                
                # Sorteer opties
                sort_options = ['Totaal_Kandidaten', 'Gesprekken', 'Aangenomen', 'Hire_Rate', 'Aanmaakdatum']
                sort_by = st.selectbox(
                    "Sorteer op",
                    options=sort_options,
                    index=0
                )
                
                if sort_by in ['Hire_Rate', 'Gesprek_Rate']:
                    # Speciale behandeling voor percentage sorting
                    detailed_analysis['Sort_Value'] = detailed_analysis[sort_by].str.replace('%', '').astype(float)
                    detailed_analysis = detailed_analysis.sort_values('Sort_Value', ascending=False)
                    detailed_analysis = detailed_analysis.drop('Sort_Value', axis=1)
                else:
                    detailed_analysis = detailed_analysis.sort_values(sort_by, ascending=False)
                
                # Toon tabel met nieuwe kolommen
                st.dataframe(
                    detailed_analysis,
                    use_container_width=True,
                    column_config={
                        "Vacature": st.column_config.TextColumn("Vacature", width="large"),
                        "Totaal_Kandidaten": st.column_config.NumberColumn("👥 Kandidaten", format="%d"),
                        "Gesprekken": st.column_config.NumberColumn("💬 Gesprekken", format="%d"),
                        "Afgewezen_na_Brief": st.column_config.NumberColumn("❌ Afgewezen (Brief)", format="%d"),
                        "Afgewezen_na_Gesprek": st.column_config.NumberColumn("❌ Afgewezen (Gesprek)", format="%d"),
                        "Aangenomen": st.column_config.NumberColumn("✅ Aangenomen", format="%d"),
                        "Hire_Rate": st.column_config.TextColumn("📈 Hire Rate"),
                        "Gesprek_Rate": st.column_config.TextColumn("💬 Gesprek Rate"),
                    }
                )
                
                # Performance insights uitgebreid
                if len(detailed_analysis) > 0:
                    st.subheader("📊 Performance Insights")
                    
                    # Bereken totalen
                    totaal_kandidaten = detailed_analysis['Totaal_Kandidaten'].sum()
                    totaal_gesprekken = detailed_analysis['Gesprekken'].sum()
                    totaal_aangenomen = detailed_analysis['Aangenomen'].sum()
                    totaal_afgewezen_brief = detailed_analysis['Afgewezen_na_Brief'].sum()
                    totaal_afgewezen_gesprek = detailed_analysis['Afgewezen_na_Gesprek'].sum()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Totaal Kandidaten",
                            f"{totaal_kandidaten:,}",
                            help="Som van alle kandidaten voor gefilterde vacatures"
                        )
                        
                        overall_hire_rate = (totaal_aangenomen / totaal_kandidaten * 100) if totaal_kandidaten > 0 else 0
                        st.metric(
                            "Overall Hire Rate",
                            f"{overall_hire_rate:.1f}%"
                        )
                    
                    with col2:
                        st.metric(
                            "Totaal Gesprekken",
                            f"{totaal_gesprekken:,}"
                        )
                        
                        gesprek_to_hire = (totaal_aangenomen / totaal_gesprekken * 100) if totaal_gesprekken > 0 else 0
                        st.metric(
                            "Gesprek → Hire Rate",
                            f"{gesprek_to_hire:.1f}%"
                        )
                    
                    with col3:
                        st.metric(
                            "Afgewezen na Brief",
                            f"{totaal_afgewezen_brief:,}",
                            delta=f"{(totaal_afgewezen_brief/totaal_kandidaten*100):.1f}% van totaal" if totaal_kandidaten > 0 else None
                        )
                        
                        st.metric(
                            "Afgewezen na Gesprek",
                            f"{totaal_afgewezen_gesprek:,}",
                            delta=f"{(totaal_afgewezen_gesprek/totaal_gesprekken*100):.1f}% van gesprekken" if totaal_gesprekken > 0 else None
                        )
                    
                    with col4:
                        st.metric(
                            "Totaal Aangenomen",
                            f"{totaal_aangenomen:,}",
                            delta=f"{overall_hire_rate:.1f}% van kandidaten"
                        )
                        
                        # Gemiddelde kandidaten per hire
                        kandidaten_per_hire = (totaal_kandidaten / totaal_aangenomen) if totaal_aangenomen > 0 else 0
                        st.metric(
                            "Kandidaten per Hire",
                            f"{kandidaten_per_hire:.1f}",
                            help="Hoeveel kandidaten gemiddeld nodig voor 1 hire"
                        )
                    
                    # Top performers
                    st.subheader("🏆 Top Performers")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Beste hire rate (alleen vacatures met kandidaten)
                        vacatures_met_kandidaten = detailed_analysis[detailed_analysis['Totaal_Kandidaten'] > 0]
                        if len(vacatures_met_kandidaten) > 0:
                            vacatures_met_kandidaten['Hire_Rate_Numeric'] = vacatures_met_kandidaten['Hire_Rate'].str.replace('%', '').astype(float)
                            beste_hire = vacatures_met_kandidaten.loc[vacatures_met_kandidaten['Hire_Rate_Numeric'].idxmax()]
                            st.success(f"**Beste Hire Rate:** {beste_hire['Vacature'][:25]}... ({beste_hire['Hire_Rate']})")
                    
                    with col2:
                        # Meeste gesprekken
                        if detailed_analysis['Gesprekken'].max() > 0:
                            meeste_gesprekken = detailed_analysis.loc[detailed_analysis['Gesprekken'].idxmax()]
                            st.info(f"**Meeste Gesprekken:** {meeste_gesprekken['Vacature'][:25]}... ({meeste_gesprekken['Gesprekken']} gesprekken)")
                    
                    with col3:
                        # Meeste hires
                        if detailed_analysis['Aangenomen'].max() > 0:
                            meeste_hires = detailed_analysis.loc[detailed_analysis['Aangenomen'].idxmax()]
                            st.success(f"**Meeste Hires:** {meeste_hires['Vacature'][:25]}... ({meeste_hires['Aangenomen']} hires)")
            
            with tab5:
                st.header("Afdeling Analyse")
                
                # Afdeling samenvatting
                afdeling_stats = create_afdeling_summary(df)
                
                if len(afdeling_stats) > 0:
                    st.subheader("Performance per Afdeling")
                    
                    # Visualisatie
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Vacatures per afdeling
                        fig_afd1 = px.bar(
                            afdeling_stats,
                            x='Afdeling',
                            y='Totaal_Vacatures',
                            title='Aantal Vacatures per Afdeling',
                            color='Fill_Rate',
                            color_continuous_scale='RdYlGn',
                            text='Totaal_Vacatures'
                        )
                        fig_afd1.update_traces(textposition='outside')
                        fig_afd1.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_afd1, use_container_width=True)
                    
                    with col2:
                        # Fill rate per afdeling
                        fig_afd2 = px.bar(
                            afdeling_stats,
                            x='Afdeling',
                            y='Fill_Rate',
                            title='Fill Rate per Afdeling (%)',
                            color='Fill_Rate',
                            color_continuous_scale='RdYlGn',
                            text=[f"{x:.1f}%" for x in afdeling_stats['Fill_Rate']]
                        )
                        fig_afd2.update_traces(textposition='outside')
                        fig_afd2.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_afd2, use_container_width=True)
                    
                    # Afdeling tabel
                    st.subheader("Afdeling Statistieken")
                    afdeling_display = afdeling_stats.copy()
                    afdeling_display.columns = [
                        'Afdeling', 'Totaal Vacatures', 'Totaal Reacties', 'Aantal Recruiters',
                        'Vervulde Vacatures', 'Fill Rate (%)', 'Gem. Reacties per Vacature'
                    ]
                    st.dataframe(afdeling_display, use_container_width=True)
                    
                    # Afdeling insights
                    st.subheader("🏢 Afdeling Insights")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Grootste afdeling
                        grootste_afdeling = afdeling_stats.loc[afdeling_stats['Totaal_Vacatures'].idxmax()]
                        st.info(f"**Meeste Vacatures:** {grootste_afdeling['Afdeling']} ({grootste_afdeling['Totaal_Vacatures']} vacatures)")
                    
                    with col2:
                        # Beste fill rate
                        beste_fill_rate = afdeling_stats.loc[afdeling_stats['Fill_Rate'].idxmax()]
                        st.success(f"**Beste Fill Rate:** {beste_fill_rate['Afdeling']} ({beste_fill_rate['Fill_Rate']:.1f}%)")
                    
                    with col3:
                        # Meeste recruiters
                        meeste_recruiters = afdeling_stats.loc[afdeling_stats['Aantal_Recruiters'].idxmax()]
                        st.info(f"**Meeste Recruiters:** {meeste_recruiters['Afdeling']} ({meeste_recruiters['Aantal_Recruiters']} recruiters)")
                
                else:
                    st.info("Geen afdeling data beschikbaar in de huidige dataset.")
            
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
                st.write("✅ **Recruitment Performance**")
                recruiter_stats = create_recruitment_performance_chart(df)[1]
                if len(recruiter_stats) > 0:
                    top_recruiter = recruiter_stats.sort_values('Fill_Rate', ascending=False).iloc[0]
                    st.write(f"• Actieve recruiters: {len(recruiter_stats)}")
                    st.write(f"• Beste fill rate: {top_recruiter['Eigenaar']} ({top_recruiter['Fill_Rate']:.1f}%)")
                    st.write(f"• Totaal reacties: {recruiter_stats['Aantal reacties'].sum():,}")
                
                # Gedetailleerde kandidaat metrics
                detailed_analysis = create_detailed_vacature_analysis(df)
                if len(detailed_analysis) > 0:
                    st.write("✅ **Kandidaat Proces Analyse**")
                    totaal_gesprekken = detailed_analysis['Gesprekken'].sum()
                    totaal_afgewezen_brief = detailed_analysis['Afgewezen_na_Brief'].sum()
                    totaal_afgewezen_gesprek = detailed_analysis['Afgewezen_na_Gesprek'].sum()
                    totaal_aangenomen = detailed_analysis['Aangenomen'].sum()
                    st.write(f"• Totaal gesprekken: {totaal_gesprekken:,}")
                    st.write(f"• Afgewezen na brief: {totaal_afgewezen_brief:,}")
                    st.write(f"• Afgewezen na gesprek: {totaal_afgewezen_gesprek:,}")
                    st.write(f"• Totaal aangenomen: {totaal_aangenomen:,}")
                
                # Afdeling analyse
                if 'Afdeling' in df.columns:
                    afdeling_stats = create_afdeling_summary(df)
                    if len(afdeling_stats) > 0:
                        st.write("✅ **Afdeling Analyse**")
                        st.write(f"• Aantal afdelingen: {len(afdeling_stats)}")
                        beste_afdeling = afdeling_stats.loc[afdeling_stats['Fill_Rate'].idxmax()]
                        st.write(f"• Beste afdeling: {beste_afdeling['Afdeling']} ({beste_afdeling['Fill_Rate']:.1f}%)")
                        st.write(f"• Totaal recruiters: {afdeling_stats['Aantal_Recruiters'].sum()}")
            
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
        ✅ **Recruitment Performance** - Vergelijk prestaties tussen recruiters  
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
        
        ### 🔒 GDPR Compliance:
        - **Automatische anonimisering** - contactgegevens worden verwijderd
        - **Voornaam-only** - "Ilja Noltee" wordt "Ilja"  
        - **Client-side processing** - persoonlijke data verlaat je computer niet
        - **Privacy by design** - alleen relevante data voor analyses
        
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

def apply_gdpr_compliance(df):
    """Applies GDPR compliance by removing sensitive data and anonymizing names"""
    df_clean = df.copy()
    
    # 🔴 REMOVE HIGH RISK COLUMNS (FALLBACK - always remove if present)
    high_risk_columns = [
        'Mobiel', 'E-mail', 'E-mail werk', 'Gekoppelde kandidaten',
        'Contactpersoon telefoonnummer', 'Contactpersoon e-mail',
        'Tweede contactpersoon telefoonnummer', 'Tweede contactpersoon e-mail'
    ]
    
    removed_columns = []
    for col in high_risk_columns:
        if col in df_clean.columns:
            df_clean = df_clean.drop(columns=[col])
            removed_columns.append(col)
    
    # Log removed columns for transparency
    if removed_columns:
        st.warning(f"🔒 GDPR Fallback: Volgende gevoelige kolommen automatisch verwijderd: {', '.join(removed_columns)}")
    
    # 🟡 ANONYMIZE MEDIUM RISK COLUMNS (first name only)
    medium_risk_columns = [
        'Eigenaar', 'Vacaturehouder', 'HR-adviseur', 'Eigenaar afdeling',
        'Selectiecommissielid 1', 'Selectiecommissielid 2', 'Selectiecommissielid 3',
        'Contactpersoon voor sollicitanten', 'Tweede contactpersoon voor sollicitanten'
    ]
    
    def anonymize_name(name):
        """Extract first name only for GDPR compliance"""
        if pd.isna(name) or not isinstance(name, str) or name.strip() == '':
            return name
        
        # Clean HTML entities first
        name = clean_html_entities(name)
        
        # Extract first word (first name)
        first_name = name.split()[0] if name.split() else name
        
        # Remove any remaining special characters but keep letters and common name characters
        import re
        first_name = re.sub(r'[^a-zA-ZàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž\-\'\.]', '', first_name)
        
        return first_name if first_name else 'Anoniem'
    
    anonymized_columns = []
    for col in medium_risk_columns:
        if col in df_clean.columns:
            original_count = df_clean[col].notna().sum()
            df_clean[col] = df_clean[col].apply(anonymize_name)
            if original_count > 0:
                anonymized_columns.append(col)
    
    # Log anonymized columns for transparency
    if anonymized_columns:
        st.info(f"🔒 Namen geanonimiseerd (voornaam alleen): {', '.join(anonymized_columns)}")
    
    return df_clean

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

def load_and_process_data(uploaded_file):
    """Laadt en verwerkt de ATS CSV data met GDPR compliance"""
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
        
        # Clean HTML entities in tekst kolommen BEFORE GDPR processing
        text_columns = ['Functie', 'Functietitel', 'Eigenaar', 'Vacaturehouder', 'HR-adviseur', 'Locatie']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].apply(clean_html_entities)
        
        # 🔒 APPLY GDPR COMPLIANCE (including fallback removal)
        with st.expander("🔒 GDPR Compliance Details", expanded=False):
            st.write("**Automatische privacy bescherming toegepast:**")
            st.write("✅ Contactgegevens verwijderd (telefoon, email)")
            st.write("✅ Namen geanonimiseerd naar voornaam alleen")
            st.write("✅ Client-side verwerking - data verlaat computer niet")
            
        df = apply_gdpr_compliance(df)
        
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

def create_recruitment_performance_chart(df):
    """Maakt recruitment performance chart (inclusief afdeling)"""
    # Filter alleen actieve recruiters
    df_clean = df[df['Eigenaar'].notna() & (df['Eigenaar'] != ' ') & (df['Eigenaar'] != '')]
    
    recruiter_stats = df_clean.groupby(['Eigenaar', 'Afdeling']).agg({
        'Functie': 'count',
        'Aantal reacties': 'sum'
    }).rename(columns={'Functie': 'Totaal_Vacatures'})
    
    # Flatten multi-index
    recruiter_stats = recruiter_stats.reset_index()
    
    # Bereken vervulde vacatures
    vervulde_per_recruiter = df_clean[df_clean['Status vacature'].isin(['Extern vervuld', 'Intern vervuld'])].groupby(['Eigenaar', 'Afdeling']).size().reset_index(name='Vervulde_Vacatures')
    
    # Merge data
    recruiter_stats = recruiter_stats.merge(vervulde_per_recruiter, on=['Eigenaar', 'Afdeling'], how='left')
    recruiter_stats['Vervulde_Vacatures'] = recruiter_stats['Vervulde_Vacatures'].fillna(0)
    recruiter_stats['Fill_Rate'] = (recruiter_stats['Vervulde_Vacatures'] / recruiter_stats['Totaal_Vacatures'] * 100).round(1)
    recruiter_stats['Gem_Reacties'] = (recruiter_stats['Aantal reacties'] / recruiter_stats['Totaal_Vacatures']).round(1)
    
    # Combineer naam en afdeling voor display
    recruiter_stats['Display_Name'] = recruiter_stats['Eigenaar'] + ' (' + recruiter_stats['Afdeling'].fillna('Onbekend') + ')'
    
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
            y=recruiter_stats['Display_Name'],
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
            y=recruiter_stats['Display_Name'],
            x=recruiter_stats['Fill_Rate'],
            name='Fill Rate (%)',
            orientation='h',
            marker_color='lightgreen',
            text=[f"{x:.1f}%" for x in recruiter_stats['Fill_Rate']],
            textposition='auto'
        ),
        row=1, col=2
    )
    
    fig.update_layout(height=max(400, len(recruiter_stats) * 35), showlegend=False)
    fig.update_xaxes(title_text="Aantal Vacatures", row=1, col=1)
    fig.update_xaxes(title_text="Fill Rate (%)", row=1, col=2)
    
    return fig, recruiter_stats

def create_detailed_vacature_analysis(df):
    """Maakt gedetailleerde vacature analyse met kandidaat metrics"""
    analysis_data = []
    
    for _, row in df.iterrows():
        # Basis informatie
        vacature_naam = row['Functie'][:50] + '...' if len(str(row['Functie'])) > 50 else row['Functie']
        
        # Totaal kandidaten
        totaal_kandidaten = row['Aantal reacties'] if pd.notna(row['Aantal reacties']) else 0
        
        # Gesprekken (gesprek gevoerd)
        gesprekken = row['Aantal in status: Gesprek gevoerd'] if pd.notna(row['Aantal in status: Gesprek gevoerd']) else 0
        
        # Afwijzingen
        afgewezen_na_brief = row['Aantal in status: Afgewezen na briefselectie'] if pd.notna(row['Aantal in status: Afgewezen na briefselectie']) else 0
        afgewezen_na_gesprek = row['Aantal in status: Afgewezen na gesprek'] if pd.notna(row['Aantal in status: Afgewezen na gesprek']) else 0
        
        # Aangenomen
        aangenomen = row['Aantal in status: Aangenomen'] if pd.notna(row['Aantal in status: Aangenomen']) else 0
        
        # Bereken rates
        gesprek_rate = (gesprekken / totaal_kandidaten * 100) if totaal_kandidaten > 0 else 0
        hire_rate = (aangenomen / totaal_kandidaten * 100) if totaal_kandidaten > 0 else 0
        
        analysis_data.append({
            'Vacature': vacature_naam,
            'Recruiter': row['Eigenaar'],
            'Afdeling': row['Afdeling'] if pd.notna(row['Afdeling']) else 'Onbekend',
            'Status': row['Status vacature'],
            'Totaal_Kandidaten': int(totaal_kandidaten),
            'Gesprekken': int(gesprekken),
            'Afgewezen_na_Brief': int(afgewezen_na_brief),
            'Afgewezen_na_Gesprek': int(afgewezen_na_gesprek),
            'Aangenomen': int(aangenomen),
            'Gesprek_Rate': f"{gesprek_rate:.1f}%",
            'Hire_Rate': f"{hire_rate:.1f}%",
            'Aanmaakdatum': row['Datum aanmaak'].strftime('%d-%m-%Y') if pd.notna(row['Datum aanmaak']) else 'Onbekend'
        })
    
    return pd.DataFrame(analysis_data)

def create_afdeling_summary(df):
    """Maakt samenvatting per afdeling"""
    if 'Afdeling' not in df.columns:
        return pd.DataFrame()
    
    df_clean = df[df['Afdeling'].notna()]
    
    afdeling_stats = df_clean.groupby('Afdeling').agg({
        'Functie': 'count',
        'Aantal reacties': 'sum',
        'Eigenaar': 'nunique'
    }).rename(columns={
        'Functie': 'Totaal_Vacatures',
        'Eigenaar': 'Aantal_Recruiters'
    })
    
    # Vervulde vacatures per afdeling
    vervulde_per_afdeling = df_clean[df_clean['Status vacature'].isin(['Extern vervuld', 'Intern vervuld'])].groupby('Afdeling').size()
    afdeling_stats['Vervulde_Vacatures'] = vervulde_per_afdeling.fillna(0)
    afdeling_stats['Fill_Rate'] = (afdeling_stats['Vervulde_Vacatures'] / afdeling_stats['Totaal_Vacatures'] * 100).round(1)
    afdeling_stats['Gem_Reacties_per_Vacature'] = (afdeling_stats['Aantal reacties'] / afdeling_stats['Totaal_Vacatures']).round(1)
    
    return afdeling_stats.reset_index().sort_values('Totaal_Vacatures', ascending=False)

def create_channel_analysis(df):
    """Analyseert wervingskanalen"""
    channels = ['V&VN', 'Indeed', 'Infopuntzorg', 'Zorgselect', 'Facebook', 
               'Linkedin', 'Twitter', 'Instagram', 'Via medewerker van SEIN', 'Anders']
    
    channel_data = []
    
    for channel in channels:
        total_col = f'Totaal per wervingskanaal: {channel}'
        hire
