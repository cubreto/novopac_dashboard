#!/usr/bin/env python3
"""
NovoOAC Database Manager
Handles database operations, loading, and view management for ETL pipeline
"""

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, DateTime, Numeric, Boolean
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
from config import ETL_CONFIG

logger = logging.getLogger(__name__)

class NovoOACDatabaseManager:
    """Manages database operations for NovoOAC ETL pipeline"""
    
    def __init__(self, connection_string: str = None, config: Dict = None):
        self.config = config or ETL_CONFIG
        self.connection_string = connection_string or self.config['database']['url']
        self.schema = self.config['database']['schema']
        self.table_name = self.config['database']['table_name']
        
        # Initialize database engine
        self.engine = create_engine(
            self.connection_string,
            pool_size=self.config['database']['connection_pool_size'],
            pool_timeout=self.config['database']['connection_timeout'],
            echo=False  # Set to True for SQL debugging
        )
        
        # Load result tracking
        self.load_stats = {
            'start_time': None,
            'end_time': None,
            'rows_processed': 0,
            'chunks_processed': 0,
            'errors_encountered': 0,
            'warnings_encountered': 0
        }
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                logger.info(f"✅ Database connection successful (test result: {test_value})")
                return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def create_table_schema(self, df: pd.DataFrame) -> bool:
        """Create table schema based on DataFrame structure"""
        logger.info(f"🗄️ Creating table schema for {self.table_name}...")
        
        try:
            # Drop existing table if it exists
            with self.engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {self.table_name}"))
                conn.commit()
                logger.info(f"  Dropped existing table {self.table_name}")
            
            # Create table with pandas to_sql (let it infer types)
            # We'll use a small sample to create the structure
            sample_df = df.head(1)
            sample_df.to_sql(
                name=self.table_name,
                con=self.engine,
                schema=self.schema if self.schema != 'public' else None,
                if_exists='replace',
                index=False
            )
            
            logger.info(f"✅ Created table {self.table_name} with {len(df.columns)} columns")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create table schema: {e}")
            return False
    
    def load_data(self, df: pd.DataFrame, method: str = 'replace') -> Dict[str, Any]:
        """Load DataFrame to database with comprehensive error handling"""
        
        self.load_stats['start_time'] = datetime.now()
        
        load_result = {
            'success': False,
            'rows_inserted': 0,
            'processing_time_seconds': 0,
            'chunks_processed': 0,
            'errors': [],
            'warnings': [],
            'final_row_count': 0
        }
        
        try:
            logger.info(f"🚀 Starting database load: {len(df):,} rows")
            logger.info(f"  Method: {method}")
            logger.info(f"  Target: {self.table_name}")
            
            # Validate connection first
            if not self.test_connection():
                load_result['errors'].append("Database connection failed")
                return load_result
            
            # Create/replace table schema if needed
            if method == 'replace':
                if not self.create_table_schema(df):
                    load_result['errors'].append("Failed to create table schema")
                    return load_result
            
            # Load data in chunks for better memory management and error handling
            chunk_size = self.config['performance']['chunk_size']
            total_rows = len(df)
            chunks_processed = 0
            rows_inserted = 0
            
            logger.info(f"  Loading in chunks of {chunk_size:,} rows")
            
            # Process chunks
            for chunk_start in range(0, total_rows, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_rows)
                chunk_df = df.iloc[chunk_start:chunk_end].copy()
                
                try:
                    # Load chunk to database
                    chunk_df.to_sql(
                        name=self.table_name,
                        con=self.engine,
                        schema=self.schema if self.schema != 'public' else None,
                        if_exists='append' if chunks_processed > 0 else 'replace',
                        index=False,
                        method='multi',  # Use faster multi-insert
                        chunksize=min(100, len(chunk_df))  # Sub-chunk for very large chunks
                    )
                    
                    chunks_processed += 1
                    rows_inserted += len(chunk_df)
                    
                    # Progress logging
                    progress_pct = (chunk_end / total_rows) * 100
                    logger.info(f"  Progress: {chunk_end:,}/{total_rows:,} rows ({progress_pct:.1f}%)")
                    
                except Exception as chunk_error:
                    error_msg = f"Chunk {chunks_processed + 1} failed: {str(chunk_error)}"
                    load_result['errors'].append(error_msg)
                    logger.error(f"  ❌ {error_msg}")
                    self.load_stats['errors_encountered'] += 1
                    
                    # Continue with next chunk rather than failing completely
                    continue
            
            # Record final statistics
            load_result['rows_inserted'] = rows_inserted
            load_result['chunks_processed'] = chunks_processed
            self.load_stats['rows_processed'] = rows_inserted
            self.load_stats['chunks_processed'] = chunks_processed
            
            # Verify final row count
            final_count = self._get_table_row_count()
            load_result['final_row_count'] = final_count
            
            if final_count != rows_inserted:
                warning_msg = f"Row count mismatch: inserted {rows_inserted}, found {final_count}"
                load_result['warnings'].append(warning_msg)
                logger.warning(f"  ⚠️ {warning_msg}")
            
            # Update table statistics for query optimizer
            self._update_table_statistics()
            
            # Create indexes for performance
            self._create_performance_indexes()
            
            # Mark as successful if we inserted any rows
            if rows_inserted > 0:
                load_result['success'] = True
                logger.info(f"✅ Database load completed: {rows_inserted:,} rows inserted")
            else:
                load_result['errors'].append("No rows were successfully inserted")
                logger.error("❌ Database load failed: No rows inserted")
            
        except Exception as e:
            error_msg = f"Database load failed: {str(e)}"
            load_result['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            
        finally:
            # Calculate processing time
            self.load_stats['end_time'] = datetime.now()
            processing_time = (self.load_stats['end_time'] - self.load_stats['start_time']).total_seconds()
            load_result['processing_time_seconds'] = processing_time
            
            # Performance metrics
            if processing_time > 0 and load_result['rows_inserted'] > 0:
                rows_per_second = load_result['rows_inserted'] / processing_time
                logger.info(f"  Performance: {rows_per_second:.1f} rows/second")
        
        return load_result
    
    def _get_table_row_count(self) -> int:
        """Get current row count in the table"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {self.table_name}"))
                return result.scalar()
        except Exception as e:
            logger.error(f"Failed to get row count: {e}")
            return 0
    
    def _update_table_statistics(self) -> bool:
        """Update table statistics for query optimizer"""
        try:
            with self.engine.connect() as conn:
                # PostgreSQL ANALYZE command
                conn.execute(text(f"ANALYZE {self.table_name}"))
                conn.commit()
                logger.info(f"✅ Updated statistics for {self.table_name}")
                return True
        except Exception as e:
            logger.warning(f"Failed to update table statistics: {e}")
            return False
    
    def _create_performance_indexes(self) -> bool:
        """Create indexes for common query patterns"""
        logger.info("🔍 Creating performance indexes...")
        
        indexes = [
            # Primary business key
            ("idx_proposta", "proposta"),
            ("idx_operacao", "operacao"),
            
            # Filter columns for dashboard
            ("idx_uf", "uf"),
            ("idx_repassador", "repassador"),
            ("idx_suspensiva", "suspensiva"),
            
            # Date columns for time-based queries
            ("idx_vencimento_suspensiva", "vencimento_suspensiva"),
            ("idx_data_retirada_suspensiva", "data_retirada_suspensiva"),
            
            # Analysis columns
            ("idx_dias_sem_movimentacao", "dias_sem_movimentacao")
        ]
        
        created_indexes = 0
        
        try:
            with self.engine.connect() as conn:
                for index_name, column_name in indexes:
                    try:
                        # Check if column exists first
                        check_column = conn.execute(text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = '{self.table_name}' 
                            AND column_name = '{column_name}'
                        """))
                        
                        if check_column.rowcount > 0:
                            # Create index if column exists
                            conn.execute(text(f"""
                                CREATE INDEX IF NOT EXISTS {index_name} 
                                ON {self.table_name} ({column_name})
                            """))
                            created_indexes += 1
                        
                    except Exception as idx_error:
                        logger.warning(f"  Failed to create index {index_name}: {idx_error}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return False
        
        logger.info(f"  Created {created_indexes} indexes")
        return created_indexes > 0
    
    def create_analytical_views(self) -> bool:
        """Create analytical views for dashboard queries"""
        logger.info("📊 Creating analytical views...")
        
        views = {
            'vw_novopac_suspensivas': self._get_suspensivas_view_sql(),
            'vw_novopac_situacao_atual': self._get_situacao_atual_view_sql(),
            'vw_novopac_dashboard_summary': self._get_dashboard_summary_view_sql()
        }
        
        created_views = 0
        
        try:
            with self.engine.connect() as conn:
                for view_name, view_sql in views.items():
                    try:
                        # Drop existing view
                        conn.execute(text(f"DROP VIEW IF EXISTS {view_name}"))
                        
                        # Create new view
                        conn.execute(text(view_sql))
                        created_views += 1
                        logger.info(f"  ✅ Created view: {view_name}")
                        
                    except Exception as view_error:
                        logger.error(f"  ❌ Failed to create view {view_name}: {view_error}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error creating views: {e}")
            return False
        
        logger.info(f"Created {created_views} analytical views")
        return created_views > 0
    
    def _get_suspensivas_view_sql(self) -> str:
        """Get SQL for suspensivas analysis view"""
        return f"""
        CREATE VIEW vw_novopac_suspensivas AS
        SELECT 
            proposta,
            operacao,
            uf,
            municipio_beneficiado,
            repassador,
            gigov_regov,
            suspensiva,
            vencimento_suspensiva,
            data_cumprimento_suspensiva,
            data_retirada_suspensiva,
            dias_sem_movimentacao,
            situacao_analise_suspensiva,
            valor_repasse,
            valor_empenhado,
            
            
            dias_para_vencimento,
            latitude,
            longitude,
            processado_em
        FROM {self.table_name}
        WHERE suspensiva = 'Sim'
        """
    
    def _get_situacao_atual_view_sql(self) -> str:
        """Get SQL for situação atual analysis view"""
        return f"""
        CREATE VIEW vw_novopac_situacao_atual AS
        SELECT 
            proposta,
            operacao,
            uf,
            municipio_beneficiado,
            repassador,
            situacao_atual,
            etiquetas,
            data_atualizacao_situacao_atual,
            dias_sem_movimentacao,
            
            valor_repasse,
            valor_empenhado,
            latitude,
            longitude,
            processado_em
        FROM {self.table_name}
        WHERE situacao_atual IS NOT NULL
        """
    
    def _get_dashboard_summary_view_sql(self) -> str:
        """Get SQL for dashboard summary view"""
        return f"""
        CREATE VIEW vw_novopac_dashboard_summary AS
        SELECT 
            COUNT(*) as total_operacoes,
            COUNT(CASE WHEN suspensiva = 'Sim' THEN 1 END) as total_suspensivas,
            COUNT(CASE WHEN suspensiva = 'Não' THEN 1 END) as total_sem_suspensiva,
            COUNT(CASE WHEN situacao_atual IS NOT NULL THEN 1 END) as total_com_situacao,
            COUNT(CASE WHEN data_retirada_suspensiva IS NOT NULL THEN 1 END) as suspensivas_retiradas,
            COUNT(DISTINCT uf) as total_ufs,
            COUNT(DISTINCT repassador) as total_repassadores,
            SUM(valor_repasse) as total_valor_repasse,
            SUM(valor_empenhado) as total_valor_empenhado,
            AVG(dias_sem_movimentacao) as media_dias_sem_movimentacao,
            MAX(processado_em) as ultima_atualizacao
        FROM {self.table_name}
        """
    
    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Get comprehensive data quality metrics"""
        logger.info("📋 Collecting data quality metrics...")
        
        metrics = {
            'basic_stats': {},
            'null_analysis': {},
            'categorical_analysis': {},
            'date_analysis': {},
            'financial_analysis': {}
        }
        
        try:
            with self.engine.connect() as conn:
                # Basic statistics
                basic_query = f"""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT proposta) as unique_propostas,
                    COUNT(DISTINCT operacao) as unique_operacoes,
                    COUNT(DISTINCT uf) as unique_ufs,
                    COUNT(DISTINCT repassador) as unique_repassadores,
                    MAX(processado_em) as last_processed
                FROM {self.table_name}
                """
                
                result = conn.execute(text(basic_query)).fetchone()
                metrics['basic_stats'] = {
                    'total_rows': result[0],
                    'unique_propostas': result[1],
                    'unique_operacoes': result[2],
                    'unique_ufs': result[3],
                    'unique_repassadores': result[4],
                    'last_processed': result[5]
                }
                
                # Suspensivas analysis
                suspensivas_query = f"""
                SELECT 
                    suspensiva,
                    COUNT(*) as count
                FROM {self.table_name}
                WHERE suspensiva IS NOT NULL
                GROUP BY suspensiva
                """
                
                suspensivas_result = conn.execute(text(suspensivas_query)).fetchall()
                metrics['categorical_analysis']['suspensiva'] = {
                    row[0]: row[1] for row in suspensivas_result
                }
                
                # Financial totals
                financial_query = f"""
                SELECT 
                    SUM(valor_repasse) as total_repasse,
                    SUM(valor_empenhado) as total_empenhado,
                    AVG(valor_repasse) as media_repasse,
                    COUNT(CASE WHEN valor_repasse > 0 THEN 1 END) as operacoes_com_valor
                FROM {self.table_name}
                """
                
                financial_result = conn.execute(text(financial_query)).fetchone()
                metrics['financial_analysis'] = {
                    'total_repasse': float(financial_result[0]) if financial_result[0] else 0,
                    'total_empenhado': float(financial_result[1]) if financial_result[1] else 0,
                    'media_repasse': float(financial_result[2]) if financial_result[2] else 0,
                    'operacoes_com_valor': financial_result[3]
                }
                
                logger.info("✅ Data quality metrics collected")
                
        except Exception as e:
            logger.error(f"Failed to collect data quality metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    def export_sample_data(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """Export sample data for validation"""
        try:
            query = f"""
            SELECT * FROM {self.table_name} 
            ORDER BY processado_em DESC 
            LIMIT {limit}
            """
            
            df = pd.read_sql(query, self.engine)
            logger.info(f"✅ Exported {len(df)} sample records")
            return df
            
        except Exception as e:
            logger.error(f"Failed to export sample data: {e}")
            return None
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old processing runs (if maintaining history)"""
        try:
            cutoff_date = datetime.now() - pd.DateOffset(days=days_to_keep)
            
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    DELETE FROM {self.table_name} 
                    WHERE processado_em < '{cutoff_date}'
                """))
                
                deleted_rows = result.rowcount
                conn.commit()
                
                if deleted_rows > 0:
                    logger.info(f"🗑️ Cleaned up {deleted_rows} old records")
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False

if __name__ == "__main__":
    # Test database manager
    print("NovoOAC Database Manager Test")
    print("="*40)
    
    try:
        db_manager = NovoOACDatabaseManager()
        
        if db_manager.test_connection():
            print("✅ Database connection test passed")
            
            # Test with sample data
            sample_data = pd.DataFrame({
                'proposta': ['TEST/2025'],
                'operacao': [9999999],
                'uf': ['SP'],
                'suspensiva': ['Sim'],
                'valor_repasse': [1000000.0],
                'processado_em': [datetime.now()]
            })
            
            result = db_manager.load_data(sample_data, method='replace')
            if result['success']:
                print(f"✅ Sample data load test passed: {result['rows_inserted']} rows")
                
                # Test metrics
                metrics = db_manager.get_data_quality_metrics()
                print(f"✅ Data quality metrics: {metrics['basic_stats']}")
            else:
                print(f"❌ Sample data load failed: {result['errors']}")
        else:
            print("❌ Database connection test failed")
            
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
