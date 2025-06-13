#!/usr/bin/env python3
"""
NovoOAC Dashboard - Main Application
Professional CAIXA-branded dashboard for managing Novo PAC operations
"""

import streamlit as st
import pandas as pd
import sqlalchemy as sa
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import sys

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Import custom modules
from utils import get_database_connection

# Page configuration
st.set_page_config(
    page_title="NovoOAC Dashboard - Gestão de Suspensivas",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css(*files):
    """Inject one or more CSS files located in ../static/"""
    for css in files:
        css_path = Path(__file__).parent.parent / "static" / css
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
        else:
            st.warning(f"CSS file not found: {css_path}")

def load_dashboard_data():
    """Load key dashboard data from the database"""
    engine = get_database_connection()
    if not engine:
        return None, None, None
    
    try:
        # Load summary data
        summary_query = """
        SELECT 
            COUNT(*) as total_operacoes,
            COUNT(CASE WHEN suspensiva = 'Sim' THEN 1 END) as total_suspensivas,
            COUNT(CASE WHEN suspensiva = 'Não' THEN 1 END) as total_sem_suspensiva,
            COUNT(DISTINCT uf) as total_ufs,
            COUNT(DISTINCT repassador) as total_repassadores,
            SUM(valor_repasse) as total_valor_repasse,
            AVG(dias_sem_movimentacao) as media_dias_sem_movimentacao
        FROM novopac_ogu_data
        """
        
        summary_df = pd.read_sql(summary_query, engine)
        
        # Load suspensivas data
        suspensivas_query = """
        SELECT 
            proposta,
            uf,
            municipio_beneficiado,
            repassador,
            suspensiva,
            vencimento_suspensiva,
            dias_sem_movimentacao,
            valor_repasse,
            situacao_analise_suspensiva
        FROM novopac_ogu_data 
        WHERE suspensiva = 'Sim'
        ORDER BY dias_sem_movimentacao DESC NULLS LAST
        LIMIT 1000
        """
        
        suspensivas_df = pd.read_sql(suspensivas_query, engine)
        
        # Load UF distribution
        uf_query = """
        SELECT 
            uf,
            COUNT(*) as operacoes,
            COUNT(CASE WHEN suspensiva = 'Sim' THEN 1 END) as suspensivas,
            SUM(valor_repasse) as valor_total
        FROM novopac_ogu_data
        GROUP BY uf
        ORDER BY operacoes DESC
        """
        
        uf_df = pd.read_sql(uf_query, engine)
        
        return summary_df, suspensivas_df, uf_df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None, None, None

def render_header():
    """Render the main dashboard header"""
    st.markdown("""
    <div class="main-header">
        <h1>🏛️ NovoOAC Dashboard</h1>
        <p style="font-size: 1.2rem; margin: 0; color: white;">
            Gestão Inteligente da Carteira de Operações Contratadas
        </p>
        <p style="font-size: 0.9rem; margin-top: 0.5rem; color: rgba(255,255,255,0.8);">
            Sistema de Monitoramento de Suspensivas • Atualizado em Tempo Real
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_summary_metrics(summary_df):
    """Render key summary metrics with enhanced styling"""
    if summary_df is None or summary_df.empty:
        st.error("❌ Dados de resumo não disponíveis")
        return
    
    row = summary_df.iloc[0]
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-label">Total de Operações</div>
            <div class="kpi-number">{row['total_operacoes']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card highlight">
            <div class="kpi-label">Com Suspensiva</div>
            <div class="kpi-number">{row['total_suspensivas']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-label">Estados (UFs)</div>
            <div class="kpi-number">{row['total_ufs']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        valor_bi = row['total_valor_repasse'] / 1_000_000_000 if row['total_valor_repasse'] else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-label">Valor Total (R$ Bi)</div>
            <div class="kpi-number">{valor_bi:.1f}</div>
        </div>
        """, unsafe_allow_html=True)

def apply_chart_styling():
    """Apply consistent styling for Plotly charts"""
    return {
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'font': {
            'color': 'white',
            'family': 'Inter, sans-serif'
        },
        'title': {
            'font': {
                'color': '#FFD700',
                'size': 16,
                'family': 'Inter, sans-serif'
            }
        },
        'xaxis': {
            'gridcolor': 'rgba(255,255,255,0.1)',
            'color': 'white'
        },
        'yaxis': {
            'gridcolor': 'rgba(255,255,255,0.1)',
            'color': 'white'
        }
    }

def create_uf_chart(df_filtrado):
    """Create UF distribution chart with consistent styling"""
    if df_filtrado.empty:
        return None
    
    uf_chart_data = df_filtrado['uf'].value_counts().head(10)
    
    fig_uf = px.bar(
        x=uf_chart_data.index,
        y=uf_chart_data.values,
        title="Top 10 Estados por Operações",
        labels={'x': 'UF', 'y': 'Operações'},
        color=uf_chart_data.values,
        color_continuous_scale='Blues'
    )
    
    # Apply consistent chart styling
    chart_style = apply_chart_styling()
    fig_uf.update_layout(**chart_style)
    
    return fig_uf

def create_temporal_chart(df_filtrado):
    """Create temporal distribution chart with consistent styling"""
    if df_filtrado.empty or df_filtrado['dias_sem_movimentacao'].isna().all():
        return None
    
    fig_hist = px.histogram(
        df_filtrado,
        x='dias_sem_movimentacao',
        title="Distribuição: Dias sem Movimentação",
        labels={'x': 'Dias', 'y': 'Frequência'},
        nbins=20,
        color_discrete_sequence=['#FFD700']
    )
    
    # Apply consistent chart styling
    chart_style = apply_chart_styling()
    fig_hist.update_layout(**chart_style)
    
    return fig_hist

def render_suspensivas_filters(suspensivas_df):
    """Render sidebar filters for suspensivas tab"""
    st.sidebar.header("🎛️ Filtros")
    
    # UF filter
    ufs_disponiveis = sorted(suspensivas_df['uf'].dropna().unique())
    ufs_selecionadas = st.sidebar.multiselect(
        "Estados (UF)",
        options=ufs_disponiveis,
        default=ufs_disponiveis[:5],  # Show first 5 by default
        help="Selecione os estados para análise"
    )
    
    # Repassador filter
    repassadores_disponiveis = sorted(suspensivas_df['repassador'].dropna().unique())
    repassadores_selecionados = st.sidebar.multiselect(
        "Repassador",
        options=repassadores_disponiveis,
        default=repassadores_disponiveis,
        help="Selecione os repassadores"
    )
    
    # Days filter
    max_dias = int(suspensivas_df['dias_sem_movimentacao'].max()) if not suspensivas_df['dias_sem_movimentacao'].isna().all() else 365
    dias_filtro = st.sidebar.slider(
        "Dias sem movimentação (máx)",
        min_value=0,
        max_value=max_dias,
        value=max_dias,
        help="Filtrar por dias sem movimentação"
    )
    
    return ufs_selecionadas, repassadores_selecionados, dias_filtro

def apply_filters(suspensivas_df, ufs_selecionadas, repassadores_selecionados, dias_filtro):
    """Apply filters to the suspensivas dataframe"""
    df_filtrado = suspensivas_df.copy()
    
    if ufs_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['uf'].isin(ufs_selecionadas)]
    
    if repassadores_selecionados:
        df_filtrado = df_filtrado[df_filtrado['repassador'].isin(repassadores_selecionados)]
    
    df_filtrado = df_filtrado[
        (df_filtrado['dias_sem_movimentacao'].fillna(0) <= dias_filtro)
    ]
    
    return df_filtrado

def render_filtered_metrics(df_filtrado):
    """Render metrics for filtered data"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Operações Filtradas", f"{len(df_filtrado):,}")
    
    with col2:
        valor_filtrado = df_filtrado['valor_repasse'].sum() / 1_000_000_000
        st.metric("Valor Filtrado (R$ Bi)", f"{valor_filtrado:.2f}")
    
    with col3:
        dias_media = df_filtrado['dias_sem_movimentacao'].mean()
        st.metric("Média Dias s/ Mov.", f"{dias_media:.0f}" if not pd.isna(dias_media) else "N/A")

def render_data_table(df_filtrado):
    """Render the operations data table with export functionality"""
    st.subheader("📋 Detalhamento das Operações")
    
    # Display options
    colunas_exibir = st.multiselect(
        "Colunas a exibir:",
        options=df_filtrado.columns.tolist(),
        default=['proposta', 'uf', 'municipio_beneficiado', 'repassador', 'dias_sem_movimentacao', 'valor_repasse'],
        help="Selecione as colunas para visualização"
    )
    
    if colunas_exibir:
        # Format the dataframe for display
        df_display = df_filtrado[colunas_exibir].copy()
        
        # Format currency if valor_repasse is selected
        if 'valor_repasse' in df_display.columns:
            df_display['valor_repasse'] = df_display['valor_repasse'].apply(
                lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "N/A"
            )
        
        st.dataframe(
            df_display,
            use_container_width=True,
            height=400
        )
        
        # Export functionality
        if st.button("📥 Exportar dados filtrados (CSV)"):
            csv = df_display.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"suspensivas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

def render_suspensivas_tab(suspensivas_df):
    """Render the Suspensivas tab with real data and enhanced organization"""
    st.header("🔍 Gestão de Suspensivas")
    
    if suspensivas_df is None or suspensivas_df.empty:
        st.warning("⚠️ Dados de suspensivas não disponíveis")
        return
    
    # Render filters
    ufs_selecionadas, repassadores_selecionados, dias_filtro = render_suspensivas_filters(suspensivas_df)
    
    # Apply filters
    df_filtrado = apply_filters(suspensivas_df, ufs_selecionadas, repassadores_selecionados, dias_filtro)
    
    # Show filtered metrics
    render_filtered_metrics(df_filtrado)
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribuição por UF")
        fig_uf = create_uf_chart(df_filtrado)
        if fig_uf:
            st.plotly_chart(fig_uf, use_container_width=True)
    
    with col2:
        st.subheader("⏱️ Distribuição Temporal")
        fig_hist = create_temporal_chart(df_filtrado)
        if fig_hist:
            st.plotly_chart(fig_hist, use_container_width=True)
    
    # Data table
    render_data_table(df_filtrado)

def render_placeholder_tab(tab_name, description):
    """Render placeholder content for tabs under development"""
    st.header(f"{tab_name}")
    st.info(f"🚧 Em desenvolvimento - {description}")

def main():
    """Main dashboard application"""
    
    # 1. Load CSS styling first
    load_css("base_caixa_dark.css", "filters_modern.css")
    
    # 2. Render header
    render_header()
    
    # 3. Load data with loading indicator
    with st.spinner("🔄 Carregando dados do sistema..."):
        summary_df, suspensivas_df, uf_df = load_dashboard_data()
    
    if summary_df is not None:
        # Render summary metrics
        render_summary_metrics(summary_df)
        
        # Create tabs
        tabs = st.tabs([
            "🔍 Suspensivas", 
            "📊 Retiradas", 
            "📈 Status", 
            "📉 Indicadores", 
            "🔎 Análises", 
            "🎯 Atuação", 
            "📝 Relatório"
        ])
        
        # Suspensivas Tab (Full Implementation)
        with tabs[0]:
            render_suspensivas_tab(suspensivas_df)
        
        # Other tabs (Placeholders for now)
        with tabs[1]:
            render_placeholder_tab("📊 Retiradas", "Acompanhamento de retiradas de suspensivas")
            
        with tabs[2]:
            render_placeholder_tab("📈 Status", "Análise de status das operações")
            
        with tabs[3]:
            render_placeholder_tab("📉 Indicadores", "KPIs e indicadores de performance")
            
        with tabs[4]:
            render_placeholder_tab("🔎 Análises", "Análises avançadas e correlações")
            
        with tabs[5]:
            render_placeholder_tab("🎯 Atuação", "Planos de ação e priorização")
            
        with tabs[6]:
            render_placeholder_tab("📝 Relatório", "Relatórios detalhados e exportações")
    
    else:
        st.error("❌ Não foi possível carregar os dados. Verifique a conexão com o banco de dados.")
        st.info("💡 Certifique-se de que o PostgreSQL está rodando e o ETL foi executado com sucesso.")

if __name__ == "__main__":
    main()
