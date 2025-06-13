#!/usr/bin/env python3
"""
NovoOAC Data Transformations
Handles data cleaning, transformation, and preparation for database loading
Based on real 4,899 operations × 78 columns dataset characteristics
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import re
from typing import Dict, List, Optional, Tuple
from config import ETL_CONFIG

logger = logging.getLogger(__name__)

class NovoOACTransformer:
    """Handles data transformation and cleaning for NovoOAC dataset"""
    
    def __init__(self, config: Dict = None):
        self.config = config or ETL_CONFIG
        self.transformation_config = self.config['transformation']
        self.column_mapping = self.transformation_config['column_mapping']
        self.data_types = self.transformation_config['data_types']
        self.categorical_mappings = self.transformation_config['categorical_mappings']
        self.null_handling = self.transformation_config['null_handling']
        
        # Transformation statistics
        self.transform_stats = {
            'original_rows': 0,
            'final_rows': 0,
            'columns_mapped': 0,
            'columns_transformed': 0,
            'data_issues_fixed': 0,
            'processing_time_seconds': 0
        }
    
    def transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main transformation pipeline"""
        start_time = datetime.now()
        
        logger.info("🔄 Starting data transformation pipeline")
        logger.info(f"Input: {len(df):,} rows × {len(df.columns)} columns")
        
        self.transform_stats['original_rows'] = len(df)
        
        # Step 1: Create a copy to avoid modifying original
        df_transformed = df.copy()
        
        # Step 2: Map column names to database-friendly format
        df_transformed = self._map_column_names(df_transformed)
        
        # Step 3: Clean and standardize text columns
        df_transformed = self._clean_text_columns(df_transformed)
        
        # Step 4: Transform date columns with Brazilian formats
        df_transformed = self._transform_date_columns(df_transformed)
        
        # Step 5: Transform numeric columns (financial, counters)
        df_transformed = self._transform_numeric_columns(df_transformed)
        
        # Step 6: Handle categorical columns (Sim/Não, etc.)
        df_transformed = self._transform_categorical_columns(df_transformed)
        
        # Step 7: Handle geographic coordinates
        df_transformed = self._transform_geographic_columns(df_transformed)
        
        # Step 8: Apply null handling rules
        df_transformed = self._apply_null_handling(df_transformed)
        
        # Step 9: Compute derived fields for analysis
        df_transformed = self._compute_derived_fields(df_transformed)
        
        # Step 10: Final data quality checks and cleanup
        df_transformed = self._final_cleanup(df_transformed)
        
        # Record final statistics
        self.transform_stats['final_rows'] = len(df_transformed)
        self.transform_stats['processing_time_seconds'] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Transformation complete: {len(df_transformed):,} rows × {len(df_transformed.columns)} columns")
        logger.info(f"Processing time: {self.transform_stats['processing_time_seconds']:.2f} seconds")
        
        return df_transformed
    
    def _map_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map Portuguese column names to database-friendly English names"""
        logger.info("📝 Mapping column names...")
        
        # Track mapping statistics
        mapped_columns = 0
        unmapped_columns = []
        
        # Apply column mapping
        rename_dict = {}
        for original_col in df.columns:
            if original_col in self.column_mapping:
                mapped_name = self.column_mapping[original_col]
                rename_dict[original_col] = mapped_name
                mapped_columns += 1
            else:
                # Create a safe column name for unmapped columns
                safe_name = self._create_safe_column_name(original_col)
                rename_dict[original_col] = safe_name
                unmapped_columns.append(original_col)
        
        df_mapped = df.rename(columns=rename_dict)
        
        self.transform_stats['columns_mapped'] = mapped_columns
        
        logger.info(f"  Mapped {mapped_columns} columns")
        if unmapped_columns:
            logger.warning(f"  {len(unmapped_columns)} unmapped columns (will use safe names)")
            for col in unmapped_columns[:5]:  # Show first 5
                logger.warning(f"    Unmapped: '{col}' -> '{rename_dict[col]}'")
        
        return df_mapped
    
    def _create_safe_column_name(self, column_name: str) -> str:
        """Create a database-safe column name"""
        # Convert to string and clean
        safe_name = str(column_name).strip().lower()
        
        # Replace special characters
        safe_name = re.sub(r'[áàâãä]', 'a', safe_name)
        safe_name = re.sub(r'[éèêë]', 'e', safe_name)
        safe_name = re.sub(r'[íìîï]', 'i', safe_name)
        safe_name = re.sub(r'[óòôõö]', 'o', safe_name)
        safe_name = re.sub(r'[úùûü]', 'u', safe_name)
        safe_name = re.sub(r'[ç]', 'c', safe_name)
        
        # Replace spaces and special chars with underscores
        safe_name = re.sub(r'[^a-z0-9_]', '_', safe_name)
        
        # Remove multiple underscores
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # Remove leading/trailing underscores
        safe_name = safe_name.strip('_')
        
        # Ensure it doesn't start with a number
        if safe_name and safe_name[0].isdigit():
            safe_name = 'col_' + safe_name
        
        return safe_name or 'unnamed_column'
    
    def _clean_text_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize text columns"""
        logger.info("🧹 Cleaning text columns...")
        
        text_columns = [col for col in df.columns if col in self.data_types['text_columns']]
        issues_fixed = 0
        
        for col in text_columns:
            if col in df.columns:
                original_nulls = df[col].isnull().sum()
                
                # Convert to string and handle NaN
                df[col] = df[col].astype(str)
                
                # Replace pandas NaN representations
                df[col] = df[col].replace(['nan', 'NaN', '<NA>', 'None', 'null'], None)
                
                # Strip whitespace
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) and x != 'None' else x)
                
                # Replace empty strings with None
                df[col] = df[col].replace('', None)
                
                # Specific cleaning by column type
                if col == 'uf':
                    df[col] = self._clean_uf_column(df[col])
                elif col == 'suspensiva':
                    df[col] = self._clean_suspensiva_column(df[col])
                elif col in ['situacao_atual', 'etiquetas']:
                    df[col] = self._clean_text_analysis_columns(df[col])
                
                # Count issues fixed
                new_nulls = df[col].isnull().sum()
                issues_fixed += abs(new_nulls - original_nulls)
        
        self.transform_stats['data_issues_fixed'] += issues_fixed
        logger.info(f"  Cleaned {len(text_columns)} text columns")
        
        return df
    
    def _clean_uf_column(self, series: pd.Series) -> pd.Series:
        """Clean UF (state) column with validation"""
        # Convert to uppercase
        series = series.apply(lambda x: x.upper() if isinstance(x, str) else x)
        
        # Validate against known Brazilian states
        valid_ufs = set(self.transformation_config['valid_ufs'])
        
        def validate_uf(value):
            if pd.isna(value) or value is None:
                return None
            if isinstance(value, str) and value in valid_ufs:
                return value
            # Log invalid UF for monitoring
            logger.warning(f"Invalid UF code found: {value}")
            return None
        
        return series.apply(validate_uf)
    
    def _clean_suspensiva_column(self, series: pd.Series) -> pd.Series:
        """Clean Suspensiva column to standardize Sim/Não values"""
        mapping = self.categorical_mappings['suspensiva']
        
        def clean_suspensiva(value):
            if pd.isna(value) or value is None:
                return None
            str_value = str(value).strip()
            return mapping.get(str_value, str_value)  # Return mapped value or original
        
        return series.apply(clean_suspensiva)
    
    def _clean_text_analysis_columns(self, series: pd.Series) -> pd.Series:
        """Clean text columns used for analysis (situacao_atual, etiquetas)"""
        def clean_text(value):
            if pd.isna(value) or value is None:
                return None
            
            # Ensure it's a string
            text = str(value)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove leading dashes and cleanup
            text = re.sub(r'^[-\s]+', '', text)
            
            # Return None if empty after cleaning
            return text.strip() if text.strip() else None
        
        return series.apply(clean_text)
    
    def _transform_date_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform date columns handling various formats"""
        logger.info("📅 Transforming date columns...")
        
        date_columns = [col for col in df.columns if col in self.data_types['date_columns']]
        transformed_count = 0
        
        for col in date_columns:
            if col in df.columns:
                original_type = df[col].dtype
                
                try:
                    # Handle different date formats
                    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                    
                    # Remove unrealistic future dates (likely data errors)
                    future_cutoff = pd.Timestamp.now() + pd.DateOffset(years=5)
                    future_mask = df[col] > future_cutoff
                    if future_mask.any():
                        logger.warning(f"  Removing {future_mask.sum()} unrealistic future dates in {col}")
                        df.loc[future_mask, col] = None
                    
                    # Remove unrealistic past dates for certain columns
                    if col in ['vencimento_suspensiva', 'data_atualizacao']:
                        past_cutoff = pd.Timestamp('2020-01-01')
                        past_mask = df[col] < past_cutoff
                        if past_mask.any():
                            logger.warning(f"  Removing {past_mask.sum()} unrealistic past dates in {col}")
                            df.loc[past_mask, col] = None
                    
                    transformed_count += 1
                    
                except Exception as e:
                    logger.error(f"  Error transforming date column {col}: {e}")
        
        logger.info(f"  Transformed {transformed_count} date columns")
        return df
    
    def _transform_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform numeric columns (integers and decimals)"""
        logger.info("🔢 Transforming numeric columns...")
        
        # Integer columns
        integer_columns = [col for col in df.columns if col in self.data_types['integer_columns']]
        for col in integer_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')  # Nullable integer
        
        # Decimal columns (financial values, coordinates)
        decimal_columns = [col for col in df.columns if col in self.data_types['decimal_columns']]
        for col in decimal_columns:
            if col in df.columns:
                # Handle Brazilian number format if needed
                if df[col].dtype == 'object':
                    # Check if this might be Brazilian format (comma as decimal)
                    sample_values = df[col].dropna().astype(str).head(10)
                    if any(',' in str(val) and '.' in str(val) for val in sample_values):
                        # Brazilian format: 1.234,56 -> 1234.56
                        df[col] = df[col].astype(str).str.replace('.', '', regex=False)  # Remove thousands
                        df[col] = df[col].str.replace(',', '.', regex=False)  # Decimal separator
                
                # Convert to numeric
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Validate ranges for financial columns
                if col in ['valor_repasse', 'valor_empenhado', 'valor_investimento']:
                    # Remove negative values (shouldn't exist in financial data)
                    negative_mask = df[col] < 0
                    if negative_mask.any():
                        logger.warning(f"  Removing {negative_mask.sum()} negative values in {col}")
                        df.loc[negative_mask, col] = None
                    
                    # Flag unrealistic values (over R$ 2 billion)
                    large_mask = df[col] > 2_000_000_000
                    if large_mask.any():
                        logger.warning(f"  Found {large_mask.sum()} very large values in {col} (>R$ 2B)")
        
        logger.info(f"  Transformed {len(integer_columns)} integer and {len(decimal_columns)} decimal columns")
        return df
    
    def _transform_categorical_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform categorical columns with standardized values"""
        logger.info("📊 Transforming categorical columns...")
        
        for col, mapping in self.categorical_mappings.items():
            if col in df.columns:
                original_values = df[col].value_counts()
                df[col] = df[col].map(mapping).fillna(df[col])  # Keep unmapped values
                new_values = df[col].value_counts()
                
                logger.info(f"  {col}: {dict(new_values)}")
        
        return df
    
    def _transform_geographic_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform and validate geographic coordinates"""
        logger.info("🌍 Transforming geographic columns...")
        
        if 'latitude' in df.columns and 'longitude' in df.columns:
            # Validate coordinate ranges for Brazil
            # Brazil: Latitude -33.75 to 5.27, Longitude -73.98 to -28.85
            
            lat_col, lon_col = 'latitude', 'longitude'
            
            # Validate latitude
            if lat_col in df.columns:
                invalid_lat = (df[lat_col] < -35) | (df[lat_col] > 10)
                if invalid_lat.any():
                    logger.warning(f"  Removing {invalid_lat.sum()} invalid latitude values")
                    df.loc[invalid_lat, lat_col] = None
            
            # Validate longitude  
            if lon_col in df.columns:
                invalid_lon = (df[lon_col] < -75) | (df[lon_col] > -25)
                if invalid_lon.any():
                    logger.warning(f"  Removing {invalid_lon.sum()} invalid longitude values")
                    df.loc[invalid_lon, lon_col] = None
            
            # Remove coordinates where one is null but other isn't
            if lat_col in df.columns and lon_col in df.columns:
                mismatched = df[lat_col].isnull() != df[lon_col].isnull()
                if mismatched.any():
                    logger.warning(f"  Removing {mismatched.sum()} mismatched coordinate pairs")
                    df.loc[mismatched, [lat_col, lon_col]] = None
        
        return df
    
    def _apply_null_handling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply null handling rules based on business logic"""
        logger.info("🔧 Applying null handling rules...")
        
        # Preserve nulls in expected high-null columns
        preserve_null_cols = self.null_handling['preserve_null']
        logger.info(f"  Preserving nulls in {len(preserve_null_cols)} columns (expected pattern)")
        
        # Apply default values if specified
        default_values = self.null_handling.get('default_values', {})
        for col, default_val in default_values.items():
            if col in df.columns:
                null_count = df[col].isnull().sum()
                df[col] = df[col].fillna(default_val)
                logger.info(f"  Applied default value to {null_count} nulls in {col}")
        
        # Validate required non-null columns
        required_cols = self.null_handling['required_not_null']
        for col in required_cols:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    logger.warning(f"  Required column {col} has {null_count} null values")
        
        return df
    
    def _compute_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute derived fields for dashboard analysis"""
        logger.info("⚙️ Computing derived fields...")
        
        # Urgency classification based on days without movement
        if 'dias_sem_movimentacao' in df.columns:
            conditions = [
                (df['dias_sem_movimentacao'] > 120),  # Critical
                (df['dias_sem_movimentacao'] > 90),   # Urgent  
                (df['dias_sem_movimentacao'] > 60),   # Attention
                (df['dias_sem_movimentacao'] > 0)     # Normal
            ]
            choices = ['Crítico', 'Urgente', 'Atenção', 'Normal']
#             df['status_urgencia'] = np.select(conditions, choices, default='Sem Dados')
        
        # Days until/since suspension expiry
        if 'vencimento_suspensiva' in df.columns:
            today = pd.Timestamp.now().normalize()
            df['dias_para_vencimento'] = (df['vencimento_suspensiva'] - today).dt.days
        
        # Financial execution percentage
        if 'valor_empenhado' in df.columns and 'valor_repasse' in df.columns:
            df['percentual_empenhado'] = np.where(
                df['valor_repasse'] > 0,
                (df['valor_empenhado'] / df['valor_repasse'] * 100).round(2),
                None
            )
        
        # Suspension status classification
        if 'suspensiva' in df.columns and 'data_retirada_suspensiva' in df.columns:
            conditions = [
                (df['data_retirada_suspensiva'].notna()),  # Withdrawn
                (df['suspensiva'] == 'Sim'),               # Active
                (df['suspensiva'] == 'Não')                # No suspension
            ]
            choices = ['Retirada', 'Ativa', 'Sem Suspensiva']
#             df['status_suspensiva'] = np.select(conditions, choices, default='Indefinido')
        
        # Add processing timestamp
        df['processado_em'] = datetime.now()
        
        logger.info("  Computed urgency, financial, and status derived fields")
        return df
    
    def _final_cleanup(self, df: pd.DataFrame) -> pd.DataFrame:
        """Final data cleanup and validation"""
        logger.info("🧹 Final cleanup...")
        
        # Remove completely empty rows
        initial_rows = len(df)
        df = df.dropna(how='all')
        removed_empty = initial_rows - len(df)
        if removed_empty > 0:
            logger.info(f"  Removed {removed_empty} completely empty rows")
        
        # Ensure required columns are not null
        required_cols = self.null_handling['required_not_null']
        for col in required_cols:
            if col in df.columns:
                before_count = len(df)
                df = df.dropna(subset=[col])
                removed = before_count - len(df)
                if removed > 0:
                    logger.warning(f"  Removed {removed} rows with null {col}")
        
        # Log final statistics
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        null_percentage = (null_cells / total_cells) * 100 if total_cells > 0 else 0
        
        logger.info(f"  Final dataset: {len(df):,} rows × {len(df.columns)} columns")
        logger.info(f"  Null percentage: {null_percentage:.1f}%")
        
        return df
    
    def get_transformation_summary(self) -> Dict:
        """Get summary of transformation process"""
        return {
            'statistics': self.transform_stats,
            'data_quality': {
                'rows_retained': self.transform_stats['final_rows'],
                'rows_removed': self.transform_stats['original_rows'] - self.transform_stats['final_rows'],
                'retention_rate': (self.transform_stats['final_rows'] / self.transform_stats['original_rows']) * 100 if self.transform_stats['original_rows'] > 0 else 0
            },
            'performance': {
                'processing_time_seconds': self.transform_stats['processing_time_seconds'],
                'rows_per_second': self.transform_stats['final_rows'] / self.transform_stats['processing_time_seconds'] if self.transform_stats['processing_time_seconds'] > 0 else 0
            }
        }

if __name__ == "__main__":
    # Test transformation with sample data
    print("NovoOAC Data Transformations Test")
    print("="*40)
    
    # Create sample data matching real structure
    sample_data = {
        'Proposta': ['29839/2024', '24880/2024'],
        'Operação': [1090327.0, 1098347.0],
        'UF': ['BA', 'MG'],
        'Suspensiva': ['Sim', 'Não'],
        'Valor Repasse': [3250000.0, 6500000.0],
        'Situação Atual': ['Aguarda documentação', 'Em análise'],
        'Dias sem movimentação': [45, None]
    }
    
    df_sample = pd.DataFrame(sample_data)
    
    transformer = NovoOACTransformer()
    df_transformed = transformer.transform_dataframe(df_sample)
    
    print("Sample transformation:")
    print(df_transformed)
    
    summary = transformer.get_transformation_summary()
    print(f"\nTransformation summary: {summary}")
