#!/usr/bin/env python3
"""
NovoOAC ETL Configuration
Centralized configuration for the ETL pipeline based on real data characteristics
"""

import os
from pathlib import Path
from typing import Dict, Any

# Database configuration
DATABASE_CONFIG = {
    'local_url': 'postgresql+psycopg://novopac_user:novopac_pass@localhost:5435/novopac_db',
    'production_url': os.getenv('DATABASE_URL', ''),
    'schema': 'public',  # Start with public schema, can add novopac schema later
    'table_name': 'novopac_ogu_data',
    'connection_pool_size': 5,
    'connection_timeout': 30
}

# File processing configuration
FILE_CONFIG = {
    'excel_file': 'data/REUNI_Operações_Novo_PAC_OGU_Interno_CAIXA_21-05-2025.xlsx',
    'sheet_name': 'Analítico Proposta',
    'encoding': 'utf-8',
    'chunk_size': 500,  # Rows per chunk for database loading
    'max_file_size_mb': 50,
    'backup_original': True,
    'backup_directory': 'backups/'
}

# Data validation configuration (based on real data analysis)
VALIDATION_CONFIG = {
    'expected_dimensions': {
        'rows_min': 4800,
        'rows_max': 5100,
        'columns_min': 75,
        'columns_max': 85
    },
    'required_columns': [
        'Proposta', 'UF', 'Município Beneficiado', 'Repassador',
        'GIGOV/REGOV', 'Programa', 'Situação da Proposta', 
        'Regime Simplificado', 'Valor Repasse'
    ],
    'key_analysis_columns': [
        'Suspensiva', 'Situação Atual', 'Etiquetas', 'Operação'
    ],
    'null_rate_thresholds': {
        'overall_max': 45.0,  # Real data: 40.03%
        'critical_columns_max': 5.0,  # Required columns
        'analysis_columns_max': 10.0   # Key analysis columns
    }
}

# Data transformation configuration
TRANSFORMATION_CONFIG = {
    # Column mapping from Portuguese Excel to database-friendly names
    'column_mapping': {
        # Core identification
        'Proposta': 'proposta',
        'Operação': 'operacao', 
        'DV': 'dv',
        'Instrumento': 'instrumento',
        
        # Entity information
        'Recebedor': 'recebedor',
        'Ente de vinculação': 'ente_vinculacao',
        'UF': 'uf',
        'Município Beneficiado': 'municipio_beneficiado',
        
        # CAIXA structure
        'GIGOV/REGOV': 'gigov_regov',
        'GIGOV de Vinculação': 'gigov_vinculacao',
        'Repassador': 'repassador',
        
        # Program information
        'Programa': 'programa',
        'Objetivo': 'objetivo',
        
        # Geographic data
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        
        # Project classification
        'Tipo': 'tipo',
        'Tipologia': 'tipologia',
        
        # Status fields
        'Situação do Termo de Compromisso': 'situacao_termo_compromisso',
        'Situação da Proposta': 'situacao_proposta',
        'Regime Simplificado': 'regime_simplificado',
        
        # Financial values
        'Valor Repasse': 'valor_repasse',
        'Valor Investimento': 'valor_investimento',
        'Valor Empenhado': 'valor_empenhado',
        'Valor Pago C.Convênio': 'valor_pago_convenio',
        'Valor Desbloqueado': 'valor_desbloqueado',
        
        # Budget
        'Ação Orçamentária': 'acao_orcamentaria',
        
        # === SUSPENSIVAS FIELDS (Critical for dashboard) ===
        'Vencimento da Suspensiva': 'vencimento_suspensiva',
        'Classificação Suspensiva': 'classificacao_suspensiva',
        'Suspensiva': 'suspensiva',
        'Data Cumprimento Suspensiva': 'data_cumprimento_suspensiva',
        'Último Envio Suspensiva (dentro do prazo contratual)': 'ultimo_envio_suspensiva_prazo',
        'Último Envio Suspensiva': 'ultimo_envio_suspensiva',
        'Última Evolução Suspensiva': 'ultima_evolucao_suspensiva',
        'Dias sem movimentação': 'dias_sem_movimentacao',
        'Prazo Suspensiva Contratual': 'prazo_suspensiva_contratual',
        'Data Retirada Suspensiva': 'data_retirada_suspensiva',
        'Qd.Complementações de Suspensiva': 'qtd_complementacoes_suspensiva',
        'Situação da Análise Suspensiva': 'situacao_analise_suspensiva',
        
        # === CURRENT STATUS ANALYSIS (Critical for dashboard) ===
        'Etiquetas': 'etiquetas',
        'Situação Atual': 'situacao_atual',
        'Data atualização da Situação Atual': 'data_atualizacao_situacao_atual',
        
        # Process timeline
        'Envio para CAIXA': 'envio_caixa',
        'PT em Complementação': 'pt_complementacao',
        'PT em Análise': 'pt_analise',
        'PT Aprovado': 'pt_aprovado',
        'Emissão Empenho': 'emissao_empenho',
        'TC Assinado': 'tc_assinado',
        
        # System fields
        'Data Atualização': 'data_atualizacao'
    },
    
    # Data type specifications
    'data_types': {
        'text_columns': [
            'proposta', 'recebedor', 'ente_vinculacao', 'uf', 'municipio_beneficiado',
            'gigov_regov', 'gigov_vinculacao', 'repassador', 'programa', 'objetivo',
            'tipo', 'tipologia', 'situacao_termo_compromisso', 'situacao_proposta',
            'regime_simplificado', 'acao_orcamentaria', 'classificacao_suspensiva',
            'suspensiva', 'situacao_analise_suspensiva', 'etiquetas', 'situacao_atual'
        ],
        'integer_columns': [
            'operacao', 'dv', 'instrumento', 'dias_sem_movimentacao',
            'qtd_complementacoes_suspensiva'
        ],
        'decimal_columns': [
            'valor_repasse', 'valor_investimento', 'valor_empenhado',
            'valor_pago_convenio', 'valor_desbloqueado', 'latitude', 'longitude'
        ],
        'date_columns': [
            'vencimento_suspensiva', 'data_cumprimento_suspensiva',
            'ultimo_envio_suspensiva_prazo', 'ultimo_envio_suspensiva',
            'ultima_evolucao_suspensiva', 'prazo_suspensiva_contratual',
            'data_retirada_suspensiva', 'data_atualizacao_situacao_atual',
            'envio_caixa', 'pt_complementacao', 'pt_analise', 'pt_aprovado',
            'emissao_empenho', 'tc_assinado', 'data_atualizacao'
        ]
    },
    
    # Categorical value mappings
    'categorical_mappings': {
        'suspensiva': {
            'Sim': 'Sim', 'sim': 'Sim', 'SIM': 'Sim', 'S': 'Sim',
            'Não': 'Não', 'Nao': 'Não', 'NAO': 'Não', 'não': 'Não', 'N': 'Não'
        },
        'regime_simplificado': {
            'Sim': 'Sim', 'sim': 'Sim', 'SIM': 'Sim',
            'Não': 'Não', 'Nao': 'Não', 'NAO': 'Não', 'não': 'Não'
        }
    },
    
    # Brazilian UF codes
    'valid_ufs': [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ],
    
    # Null handling rules
    'null_handling': {
        'preserve_null': [
            'dias_sem_movimentacao',  # 86.8% null - expected pattern
            'classificacao_suspensiva',  # 95.6% null - expected
            'latitude', 'longitude',  # 34% null - expected for some programs
            'data_cumprimento_suspensiva'  # 46% null - expected
        ],
        'default_values': {
            # Only set defaults for critical operational fields if needed
        },
        'required_not_null': [
            'proposta', 'uf', 'repassador'  # Critical business keys
        ]
    }
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_directory': 'etl_logs/',
    'log_file_pattern': 'novopac_etl_{date}.log',
    'max_log_files': 30,
    'log_to_console': True,
    'log_to_file': True
}

# Performance configuration
PERFORMANCE_CONFIG = {
    'chunk_size': 500,  # Database insert chunk size
    'memory_limit_mb': 1024,  # Max memory usage
    'connection_pool_size': 5,
    'parallel_processing': False,  # Keep simple for now
    'cache_transformed_data': True,
    'enable_progress_bars': True
}

# Monitoring configuration
MONITORING_CONFIG = {
    'enable_monitoring': True,
    'alert_on_failure': True,
    'alert_on_warnings': False,
    'quality_score_threshold': 80.0,
    'performance_thresholds': {
        'max_processing_time_minutes': 10,
        'max_memory_usage_mb': 1024,
        'min_rows_processed': 4000
    },
    'export_metrics': True,
    'metrics_file': 'etl_logs/etl_metrics.json'
}

# Environment-specific configurations
def get_config(environment: str = 'local') -> Dict[str, Any]:
    """Get configuration for specific environment"""
    
    base_config = {
        'database': DATABASE_CONFIG,
        'file': FILE_CONFIG,
        'validation': VALIDATION_CONFIG,
        'transformation': TRANSFORMATION_CONFIG,
        'logging': LOGGING_CONFIG,
        'performance': PERFORMANCE_CONFIG,
        'monitoring': MONITORING_CONFIG
    }
    
    if environment == 'local':
        # Local development overrides
        base_config['database']['url'] = DATABASE_CONFIG['local_url']
        base_config['logging']['level'] = 'DEBUG'
        base_config['performance']['chunk_size'] = 250  # Smaller for local testing
        
    elif environment == 'production':
        # Production overrides
        base_config['database']['url'] = DATABASE_CONFIG['production_url']
        base_config['logging']['level'] = 'INFO'
        base_config['monitoring']['alert_on_warnings'] = True
        base_config['performance']['chunk_size'] = 1000  # Larger for production
        
    return base_config

# Convenience function to get current config
def get_current_config() -> Dict[str, Any]:
    """Get configuration for current environment"""
    environment = os.getenv('NOVOPAC_ENV', 'local')
    return get_config(environment)

# Export main config
ETL_CONFIG = get_current_config()

# Helper functions
def get_database_url() -> str:
    """Get database URL for current environment"""
    return ETL_CONFIG['database']['url']

def get_required_columns() -> list:
    """Get list of required columns"""
    return ETL_CONFIG['validation']['required_columns']

def get_column_mapping() -> Dict[str, str]:
    """Get column mapping dictionary"""
    return ETL_CONFIG['transformation']['column_mapping']

def validate_environment():
    """Validate that environment is properly configured"""
    config = get_current_config()
    
    # Check database URL is set
    if not config['database']['url']:
        raise ValueError("Database URL not configured")
    
    # Check file exists in local environment
    env = os.getenv('NOVOPAC_ENV', 'local')
    if env == 'local':
        file_path = Path(config['file']['excel_file'])
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
    
    return True

if __name__ == "__main__":
    # Test configuration
    print("NovoOAC ETL Configuration Test")
    print("="*40)
    
    try:
        config = get_current_config()
        print(f"Environment: {os.getenv('NOVOPAC_ENV', 'local')}")
        print(f"Database URL: {config['database']['url']}")
        print(f"Excel file: {config['file']['excel_file']}")
        print(f"Required columns: {len(config['validation']['required_columns'])}")
        print(f"Column mappings: {len(config['transformation']['column_mapping'])}")
        print("✅ Configuration loaded successfully")
        
        validate_environment()
        print("✅ Environment validation passed")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
