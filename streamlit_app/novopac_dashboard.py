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

# Import the correct database connection from utils
from utils import get_database_connection

# Page configuration
st.set_page_config(
    page_title="NovoOAC Dashboard - Gestão de Suspensivas",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def apply_caixa_styling():
    """Apply enhanced CAIXA styling with perfect contrast"""
    st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* Global styling - CRITICAL: Ensure dark background always */
        .stApp {
            background: linear-gradient(135deg, #0066cc 0%, #004499 100%) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: white !important;
            min-height: 100vh;
        }
        
        /* Main app background - FORCE dark theme */
        .main { 
            background: linear-gradient(135deg, #0066cc 0%, #004499 100%) !important; 
            color: white !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* CRITICAL: Block container - ensure white text */
        .block-container {
            background: transparent !important;
            color: white !important;
            max-width: 1400px !important;
        }
        
        /* CRITICAL: All main content text must be white */
        .main p, .main div, .main span, .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
            color: white !important;
        }
        
        /* SIDEBAR STYLING */
        section[data-testid="stSidebar"] {
            background-color: #F7F9FC !important;
            border-right: 3px solid #FFD700 !important;
        }
        
        section[data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label {
            color: #1F3B75 !important;
            font-weight: 600 !important;
        }
        
        /* HEADER STYLING */
        .main-header {
            background: linear-gradient(135deg, #0066cc 0%, #004499 50%, #002975 100%) !important;
            padding: 2rem !important;
            border-radius: 20px !important;
            color: white !important;
            text-align: center !important;
            margin-bottom: 2rem !important;
            border: 3px solid #FFD700 !important;
            box-shadow: 0 15px 50px rgba(0, 102, 204, 0.4) !important;
        }
        
        .main-header h1 {
            font-size: 2.8rem !important;
            font-weight: 700 !important;
            margin-bottom: 1rem !important;
            text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.5) !important;
            background: linear-gradient(45deg, #FFD700, #FFF) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
        }
        
        /* METRIC CARDS */
        .metric-card {
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.08) 100%) !important;
            backdrop-filter: blur(15px) !important;
            padding: 1.5rem !important;
            border-radius: 20px !important;
            border: 2px solid rgba(255, 215, 0, 0.5) !important;
            margin: 1rem !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.3s ease !important;
            color: white !important;
        }
        
        .metric-card:hover {
            transform: translateY(-5px) !important;
            box-shadow: 0 20px 40px rgba(255, 215, 0, 0.3) !important;
            border-color: #FFD700 !important;
        }
        
        .kpi-number {
            font-size: 3rem !important;
            font-weight: 800 !important;
            color: #FFD700 !important;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8) !important;
            margin: 0.5rem 0 !important;
            line-height: 1.2 !important;
        }
        
        .kpi-label {
            font-size: 0.9rem !important;
            color: rgba(255, 255, 255, 0.95) !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }
        
        /* TABS STYLING */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px !important;
            background: rgba(0, 0, 0, 0.2) !important;
            padding: 8px !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            padding: 12px 24px !important;
            border: 2px solid transparent !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            color: white !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
            color: #003366 !important;
            border-color: #FFD700 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4) !important;
            font-weight: bold !important;
        }
        
        /* BUTTONS */
        .stButton > button {
            background: linear-gradient(135deg, #0066cc 0%, #004499 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.75rem 2rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(0, 102, 204, 0.4) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(0, 102, 204, 0.6) !important;
            background: linear-gradient(135deg, #004499 0%, #002975 100%) !important;
        }
        
        /* HEADERS */
        h1, h2, h3, h4, h5, h6 { 
            color: #FFD700 !important; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8) !important;
            font-weight: bold !important;
        }
        
        /* DATAFRAMES */
        .stDataFrame {
            border-radius: 15px !important;
            overflow: hidden !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
            border: 2px solid rgba(255, 215, 0, 0.4) !important;
            background: rgba(255, 255, 255, 0.98) !important;
        }
        
        /* CHARTS */
        .js-plotly-plot {
            border-radius: 15px !important;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2) !important;
            overflow: hidden !important;
            border: 2px solid rgba(255, 215, 0, 0.3) !important;
            background: rgba(255, 255, 255, 0.02) !important;
        }
    </style>
    """, unsafe_allow_html=True)

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
    """Render key summary metrics"""
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
        <div class="metric-card">
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

def render_suspensivas_tab(suspensivas_df):
    """Render the Suspensivas tab with real data"""
    st.header("🔍 Gestão de Suspensivas")
    
    if suspensivas_df is None or suspensivas_df.empty:
        st.warning("⚠️ Dados de suspensivas não disponíveis")
        return
    
    # Sidebar filters
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
    
    # Apply filters
    df_filtrado = suspensivas_df.copy()
    if ufs_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['uf'].isin(ufs_selecionadas)]
    if repassadores_selecionados:
        df_filtrado = df_filtrado[df_filtrado['repassador'].isin(repassadores_selecionados)]
    
    df_filtrado = df_filtrado[
        (df_filtrado['dias_sem_movimentacao'].fillna(0) <= dias_filtro)
    ]
    
    # Show filtered metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Operações Filtradas", f"{len(df_filtrado):,}")
    
    with col2:
        valor_filtrado = df_filtrado['valor_repasse'].sum() / 1_000_000_000
        st.metric("Valor Filtrado (R$ Bi)", f"{valor_filtrado:.2f}")
    
    with col3:
        dias_media = df_filtrado['dias_sem_movimentacao'].mean()
        st.metric("Média Dias s/ Mov.", f"{dias_media:.0f}" if not pd.isna(dias_media) else "N/A")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribuição por UF")
        if not df_filtrado.empty:
            uf_chart_data = df_filtrado['uf'].value_counts().head(10)
            fig_uf = px.bar(
                x=uf_chart_data.index,
                y=uf_chart_data.values,
                title="Top 10 Estados por Operações",
                labels={'x': 'UF', 'y': 'Operações'},
                color=uf_chart_data.values,
                color_continuous_scale='Blues'
            )
            fig_uf.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_uf, use_container_width=True)
    
    with col2:
        st.subheader("⏱️ Distribuição Temporal")
        if not df_filtrado.empty and not df_filtrado['dias_sem_movimentacao'].isna().all():
            fig_hist = px.histogram(
                df_filtrado,
                x='dias_sem_movimentacao',
                title="Distribuição: Dias sem Movimentação",
                labels={'x': 'Dias', 'y': 'Frequência'},
                nbins=20
            )
            fig_hist.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_hist, use_container_width=True)
    
    # Data table
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
        
        # Export button
        if st.button("📥 Exportar dados filtrados (CSV)"):
            csv = df_display.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"suspensivas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

def main():
    """Main dashboard application"""
    
    # Apply CAIXA styling
    apply_caixa_styling()
    
    # Render header
    render_header()
    
    # Load data
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
            st.header("📊 Retiradas")
            st.info("🚧 Em desenvolvimento - Acompanhamento de retiradas de suspensivas")
            
        with tabs[2]:
            st.header("📈 Status")
            st.info("🚧 Em desenvolvimento - Análise de status das operações")
            
        with tabs[3]:
            st.header("📉 Indicadores")
            st.info("🚧 Em desenvolvimento - KPIs e indicadores de performance")
            
        with tabs[4]:
            st.header("🔎 Análises")
            st.info("🚧 Em desenvolvimento - Análises avançadas e correlações")
            
        with tabs[5]:
            st.header("🎯 Atuação")
            st.info("🚧 Em desenvolvimento - Planos de ação e priorização")
            
        with tabs[6]:
            st.header("📝 Relatório")
            st.info("🚧 Em desenvolvimento - Relatórios detalhados e exportações")
    
    else:
        st.error("❌ Não foi possível carregar os dados. Verifique a conexão com o banco de dados.")
        st.info("💡 Certifique-se de que o PostgreSQL está rodando e o ETL foi executado com sucesso.")

if __name__ == "__main__":
    main()
