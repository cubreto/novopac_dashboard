#!/usr/bin/env python3
"""
NovoOAC Data Validator
Validates Excel data quality and structure based on real data patterns
"""

import pandas as pd
import logging
from typing import Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class NovoOACDataValidator:
    """Validates Excel data before processing based on real data characteristics"""
    
    def __init__(self):
        # Based on real data analysis: 4,899 rows × 78 columns
        self.validation_rules = {
            # File structure validation
            'expected_sheet': 'Analítico Proposta',
            'expected_rows_min': 4800,  # Allow slight variance
            'expected_rows_max': 5000,
            'expected_columns_min': 75,  # Allow slight variance
            'expected_columns_max': 85,
            
            # Required columns with 100% coverage
            'required_columns_100pct': [
                'Proposta', 'UF', 'Município Beneficiado', 'Repassador',
                'GIGOV/REGOV', 'Programa', 'Situação da Proposta', 
                'Regime Simplificado', 'Valor Repasse', 'Ação Orçamentária'
            ],
            
            # Key analysis columns with good coverage
            'analysis_columns': {
                'Suspensiva': {'min_coverage': 95.0, 'expected_values': ['Sim', 'Não']},
                'Situação Atual': {'min_coverage': 97.0},  # Real: 98.1%
                'Etiquetas': {'min_coverage': 97.0},       # Real: 98.1%
                'Operação': {'min_coverage': 97.0}         # Real: 98.1%
            },
            
            # Expected null rates (with tolerance)
            'expected_null_rates': {
                'Classificação Suspensiva': {'expected': 95.6, 'tolerance': 3.0},
                'Dias sem movimentação': {'expected': 86.8, 'tolerance': 5.0},
                'Latitude': {'expected': 34.0, 'tolerance': 5.0},
                'Longitude': {'expected': 34.0, 'tolerance': 5.0}
            },
            
            # Expected unique counts
            'expected_unique_counts': {
                'UF': {'expected': 27, 'tolerance': 0},  # Must be exactly 27 Brazilian states
                'Repassador': {'expected': 6, 'tolerance': 1},  # Expected ~6 ministries
                'Proposta': {'min_unique_pct': 99.0}  # Should be nearly all unique
            },
            
            # Data quality thresholds
            'overall_null_threshold': 45.0,  # Real data: 40.03%
            'min_file_size_mb': 8,   # Real: ~12MB
            'max_file_size_mb': 20
        }
    
    def validate_file_structure(self, file_path: str) -> Dict:
        """Validate Excel file structure and basic properties"""
        file_path = Path(file_path)
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {},
            'sheet_info': {}
        }
        
        try:
            # Check file exists and size
            if not file_path.exists():
                validation_result['valid'] = False
                validation_result['errors'].append(f"File not found: {file_path}")
                return validation_result
            
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            validation_result['file_info']['size_mb'] = round(file_size_mb, 2)
            
            # Validate file size
            if file_size_mb < self.validation_rules['min_file_size_mb']:
                validation_result['warnings'].append(
                    f"File size ({file_size_mb:.1f}MB) smaller than expected "
                    f"(>{self.validation_rules['min_file_size_mb']}MB)"
                )
            elif file_size_mb > self.validation_rules['max_file_size_mb']:
                validation_result['warnings'].append(
                    f"File size ({file_size_mb:.1f}MB) larger than expected "
                    f"(<{self.validation_rules['max_file_size_mb']}MB)"
                )
            
            # Read Excel metadata
            excel_file = pd.ExcelFile(file_path)
            validation_result['sheet_info'] = {
                'sheet_count': len(excel_file.sheet_names),
                'sheet_names': excel_file.sheet_names
            }
            
            # Check if expected sheet exists
            if self.validation_rules['expected_sheet'] not in excel_file.sheet_names:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Sheet '{self.validation_rules['expected_sheet']}' not found. "
                    f"Available sheets: {excel_file.sheet_names}"
                )
            
            logger.info(f"File validation: {file_path.name} ({file_size_mb:.1f}MB)")
            logger.info(f"Sheets: {excel_file.sheet_names}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"File structure validation failed: {str(e)}")
            logger.error(f"File structure validation error: {e}")
        
        return validation_result
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict:
        """Validate data quality against real data patterns"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'data_quality_score': 0.0
        }
        
        try:
            # Basic dimensions
            row_count = len(df)
            col_count = len(df.columns)
            validation_result['stats']['dimensions'] = {
                'rows': row_count,
                'columns': col_count
            }
            
            logger.info(f"Data validation: {row_count:,} rows × {col_count} columns")
            
            # Validate dimensions against expected
            self._validate_dimensions(df, validation_result)
            
            # Validate required columns
            self._validate_required_columns(df, validation_result)
            
            # Validate analysis columns coverage
            self._validate_analysis_columns(df, validation_result)
            
            # Validate unique counts
            self._validate_unique_counts(df, validation_result)
            
            # Validate null patterns
            self._validate_null_patterns(df, validation_result)
            
            # Validate Brazilian UF codes
            self._validate_uf_codes(df, validation_result)
            
            # Calculate overall data quality score
            validation_result['data_quality_score'] = self._calculate_quality_score(validation_result)
            
            logger.info(f"Data quality score: {validation_result['data_quality_score']:.1f}/100")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Data quality validation failed: {str(e)}")
            logger.error(f"Data quality validation error: {e}")
        
        return validation_result
    
    def _validate_dimensions(self, df: pd.DataFrame, result: Dict):
        """Validate dataset dimensions"""
        row_count = len(df)
        col_count = len(df.columns)
        
        # Check row count
        if row_count < self.validation_rules['expected_rows_min']:
            result['errors'].append(
                f"Row count too low: {row_count:,} "
                f"(expected >{self.validation_rules['expected_rows_min']:,})"
            )
            result['valid'] = False
        elif row_count > self.validation_rules['expected_rows_max']:
            result['warnings'].append(
                f"Row count higher than expected: {row_count:,} "
                f"(expected <{self.validation_rules['expected_rows_max']:,})"
            )
        
        # Check column count
        if col_count < self.validation_rules['expected_columns_min']:
            result['warnings'].append(
                f"Column count lower than expected: {col_count} "
                f"(expected >{self.validation_rules['expected_columns_min']})"
            )
        elif col_count > self.validation_rules['expected_columns_max']:
            result['warnings'].append(
                f"Column count higher than expected: {col_count} "
                f"(expected <{self.validation_rules['expected_columns_max']})"
            )
    
    def _validate_required_columns(self, df: pd.DataFrame, result: Dict):
        """Validate required columns are present"""
        missing_cols = []
        
        for col in self.validation_rules['required_columns_100pct']:
            if col not in df.columns:
                missing_cols.append(col)
        
        if missing_cols:
            result['valid'] = False
            result['errors'].append(f"Missing required columns: {missing_cols}")
        
        result['stats']['missing_required_columns'] = missing_cols
    
    def _validate_analysis_columns(self, df: pd.DataFrame, result: Dict):
        """Validate analysis columns have sufficient coverage"""
        analysis_stats = {}
        
        for col, requirements in self.validation_rules['analysis_columns'].items():
            if col in df.columns:
                coverage = (df[col].count() / len(df)) * 100
                analysis_stats[col] = {
                    'coverage_pct': round(coverage, 2),
                    'non_null_count': df[col].count(),
                    'null_count': df[col].isnull().sum()
                }
                
                if coverage < requirements['min_coverage']:
                    result['warnings'].append(
                        f"Low coverage in {col}: {coverage:.1f}% "
                        f"(expected >{requirements['min_coverage']}%)"
                    )
                
                # Check expected values if specified
                if 'expected_values' in requirements and col in df.columns:
                    unique_values = df[col].dropna().unique()
                    unexpected_values = [v for v in unique_values if v not in requirements['expected_values']]
                    if unexpected_values:
                        result['warnings'].append(
                            f"Unexpected values in {col}: {unexpected_values[:5]}"  # Show first 5
                        )
            else:
                result['warnings'].append(f"Analysis column not found: {col}")
        
        result['stats']['analysis_columns'] = analysis_stats
    
    def _validate_unique_counts(self, df: pd.DataFrame, result: Dict):
        """Validate unique value counts"""
        unique_stats = {}
        
        for col, requirements in self.validation_rules['expected_unique_counts'].items():
            if col in df.columns:
                unique_count = df[col].nunique()
                unique_stats[col] = {
                    'unique_count': unique_count,
                    'total_count': len(df)
                }
                
                if 'expected' in requirements:
                    expected = requirements['expected']
                    tolerance = requirements.get('tolerance', 0)
                    
                    if abs(unique_count - expected) > tolerance:
                        result['warnings'].append(
                            f"Unexpected unique count in {col}: {unique_count} "
                            f"(expected {expected} ± {tolerance})"
                        )
                
                if 'min_unique_pct' in requirements:
                    unique_pct = (unique_count / len(df)) * 100
                    min_pct = requirements['min_unique_pct']
                    
                    if unique_pct < min_pct:
                        result['warnings'].append(
                            f"Low uniqueness in {col}: {unique_pct:.1f}% "
                            f"(expected >{min_pct}%)"
                        )
        
        result['stats']['unique_counts'] = unique_stats
    
    def _validate_null_patterns(self, df: pd.DataFrame, result: Dict):
        """Validate null patterns match expected"""
        # Overall null percentage
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        overall_null_pct = (null_cells / total_cells) * 100
        
        result['stats']['null_analysis'] = {
            'overall_null_pct': round(overall_null_pct, 2),
            'total_cells': total_cells,
            'null_cells': null_cells
        }
        
        if overall_null_pct > self.validation_rules['overall_null_threshold']:
            result['warnings'].append(
                f"High overall null rate: {overall_null_pct:.1f}% "
                f"(threshold: {self.validation_rules['overall_null_threshold']}%)"
            )
        
        # Specific column null patterns
        column_null_stats = {}
        for col in df.columns:
            null_pct = (df[col].isnull().sum() / len(df)) * 100
            column_null_stats[col] = round(null_pct, 2)
        
        result['stats']['column_null_percentages'] = column_null_stats
        
        # Check expected null patterns
        for col, expectations in self.validation_rules['expected_null_rates'].items():
            if col in df.columns:
                actual_null_pct = column_null_stats[col]
                expected_pct = expectations['expected']
                tolerance = expectations['tolerance']
                
                if abs(actual_null_pct - expected_pct) > tolerance:
                    result['warnings'].append(
                        f"Unexpected null rate in {col}: {actual_null_pct:.1f}% "
                        f"(expected {expected_pct}% ± {tolerance}%)"
                    )
    
    def _validate_uf_codes(self, df: pd.DataFrame, result: Dict):
        """Validate UF codes are valid Brazilian states"""
        if 'UF' not in df.columns:
            return
        
        valid_ufs = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
            'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
            'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        
        unique_ufs = df['UF'].dropna().unique()
        invalid_ufs = [uf for uf in unique_ufs if uf not in valid_ufs]
        
        result['stats']['uf_validation'] = {
            'unique_ufs': len(unique_ufs),
            'valid_ufs': [uf for uf in unique_ufs if uf in valid_ufs],
            'invalid_ufs': invalid_ufs
        }
        
        if invalid_ufs:
            result['errors'].append(f"Invalid UF codes found: {invalid_ufs}")
            result['valid'] = False
    
    def _calculate_quality_score(self, result: Dict) -> float:
        """Calculate overall data quality score (0-100)"""
        score = 100.0
        
        # Deduct points for errors and warnings
        score -= len(result['errors']) * 20  # Errors are serious
        score -= len(result['warnings']) * 5   # Warnings are less serious
        
        # Ensure score doesn't go below 0
        return max(0.0, score)
    
    def generate_validation_report(self, file_validation: Dict, data_validation: Dict) -> str:
        """Generate a comprehensive validation report"""
        report_lines = [
            "="*60,
            "NOVOPAC DATA VALIDATION REPORT",
            "="*60,
            ""
        ]
        
        # File validation summary
        report_lines.extend([
            "FILE VALIDATION:",
            f"  Status: {'✅ PASSED' if file_validation['valid'] else '❌ FAILED'}",
            f"  Size: {file_validation.get('file_info', {}).get('size_mb', 'Unknown')} MB",
            f"  Sheets: {file_validation.get('sheet_info', {}).get('sheet_names', [])}",
            ""
        ])
        
        # Data validation summary
        stats = data_validation.get('stats', {})
        dims = stats.get('dimensions', {})
        
        report_lines.extend([
            "DATA VALIDATION:",
            f"  Status: {'✅ PASSED' if data_validation['valid'] else '❌ FAILED'}",
            f"  Quality Score: {data_validation.get('data_quality_score', 0):.1f}/100",
            f"  Dimensions: {dims.get('rows', 0):,} rows × {dims.get('columns', 0)} columns",
            f"  Overall Null Rate: {stats.get('null_analysis', {}).get('overall_null_pct', 0):.1f}%",
            ""
        ])
        
        # Errors
        all_errors = file_validation.get('errors', []) + data_validation.get('errors', [])
        if all_errors:
            report_lines.extend(["ERRORS:"] + [f"  ❌ {error}" for error in all_errors] + [""])
        
        # Warnings
        all_warnings = file_validation.get('warnings', []) + data_validation.get('warnings', [])
        if all_warnings:
            report_lines.extend(["WARNINGS:"] + [f"  ⚠️  {warning}" for warning in all_warnings] + [""])
        
        # Recommendations
        report_lines.extend([
            "RECOMMENDATIONS:",
            "  1. Verify data quality issues before proceeding",
            "  2. Check null patterns against business expectations", 
            "  3. Validate geographic coordinates if using map features",
            "  4. Ensure text fields are properly encoded (UTF-8)",
            ""
        ])
        
        return "\n".join(report_lines)
