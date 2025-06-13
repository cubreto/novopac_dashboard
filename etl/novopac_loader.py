#!/usr/bin/env python3
"""
NovoOAC Main ETL Orchestrator
Coordinates the complete ETL pipeline using all modular components
"""

import logging
import sys
import time
from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

# Import our modular components
from data_validator import NovoOACDataValidator
from transformations import NovoOACTransformer
from database_manager import NovoOACDatabaseManager
from config import ETL_CONFIG, validate_environment

class NovoOACETLOrchestrator:
    """Main ETL orchestrator that coordinates all pipeline components"""
    
    def __init__(self, config: Dict = None):
        self.config = config or ETL_CONFIG
        
        # Initialize components
        self.validator = NovoOACDataValidator()
        self.transformer = NovoOACTransformer(self.config)
        self.db_manager = NovoOACDatabaseManager(config=self.config)
        
        # Pipeline state
        self.pipeline_state = {
            'start_time': None,
            'end_time': None,
            'current_stage': None,
            'stages_completed': [],
            'total_duration_seconds': 0
        }
        
        # Results tracking
        self.pipeline_results = {
            'success': False,
            'stages': {},
            'final_metrics': {},
            'errors': [],
            'warnings': [],
            'data_flow': {}
        }
        
        # Setup logging
        self._setup_logging()
    
    def run_complete_pipeline(self, excel_file_path: str) -> Dict[str, Any]:
        """Execute the complete ETL pipeline"""
        
        self.pipeline_state['start_time'] = datetime.now()
        logger.info("🚀 NovoOAC ETL Pipeline Starting")
        logger.info("="*60)
        
        try:
            # Stage 1: Environment Validation
            self._execute_stage("environment_validation", self._validate_environment)
            
            # Stage 2: File Structure Validation  
            self._execute_stage("file_validation", self._validate_file_structure, excel_file_path)
            
            # Stage 3: Excel Data Loading
            self._execute_stage("data_loading", self._load_excel_data, excel_file_path)
            
            # Stage 4: Data Quality Validation
            self._execute_stage("data_quality_validation", self._validate_data_quality)
            
            # Stage 5: Data Transformation
            self._execute_stage("data_transformation", self._transform_data)
            
            # Stage 6: Database Operations
            self._execute_stage("database_loading", self._load_to_database)
            
            # Stage 7: Post-Load Operations
            self._execute_stage("post_load_operations", self._execute_post_load_operations)
            
            # Stage 8: Final Validation & Metrics
            self._execute_stage("final_validation", self._collect_final_metrics)
            
            # Pipeline completed successfully
            self.pipeline_results['success'] = True
            logger.info("🎉 ETL Pipeline Completed Successfully!")
            
        except ETLPipelineError as e:
            self.pipeline_results['errors'].append(str(e))
            logger.error(f"❌ ETL Pipeline Failed: {e}")
            
        except Exception as e:
            error_msg = f"Unexpected pipeline error: {str(e)}"
            self.pipeline_results['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            
        finally:
            self._finalize_pipeline()
        
        return self.pipeline_results
    
    def _execute_stage(self, stage_name: str, stage_function, *args, **kwargs):
        """Execute a pipeline stage with error handling and timing"""
        
        self.pipeline_state['current_stage'] = stage_name
        stage_start = datetime.now()
        
        logger.info(f"\n📍 Stage: {stage_name.replace('_', ' ').title()}")
        logger.info("-" * 40)
        
        try:
            # Execute the stage function
            stage_result = stage_function(*args, **kwargs)
            
            # Record success
            stage_duration = (datetime.now() - stage_start).total_seconds()
            self.pipeline_results['stages'][stage_name] = {
                'success': True,
                'duration_seconds': stage_duration,
                'result': stage_result,
                'timestamp': stage_start.isoformat()
            }
            
            self.pipeline_state['stages_completed'].append(stage_name)
            logger.info(f"✅ Stage completed in {stage_duration:.2f} seconds")
            
            return stage_result
            
        except Exception as e:
            # Record failure
            stage_duration = (datetime.now() - stage_start).total_seconds()
            error_msg = f"Stage {stage_name} failed: {str(e)}"
            
            self.pipeline_results['stages'][stage_name] = {
                'success': False,
                'duration_seconds': stage_duration,
                'error': error_msg,
                'timestamp': stage_start.isoformat()
            }
            
            logger.error(f"❌ {error_msg}")
            raise ETLPipelineError(f"Pipeline failed at stage '{stage_name}': {str(e)}")
    
    def _validate_environment(self) -> Dict:
        """Stage 1: Validate environment and configuration"""
        logger.info("Validating environment configuration...")
        
        try:
            validate_environment()
            
            # Test database connection
            if not self.db_manager.test_connection():
                raise Exception("Database connection failed")
            
            result = {
                'environment': 'valid',
                'database_connection': 'success',
                'config_loaded': True
            }
            
            logger.info("✅ Environment validation passed")
            return result
            
        except Exception as e:
            raise Exception(f"Environment validation failed: {e}")
    
    def _validate_file_structure(self, excel_file_path: str) -> Dict:
        """Stage 2: Validate Excel file structure"""
        logger.info(f"Validating file structure: {excel_file_path}")
        
        file_validation = self.validator.validate_file_structure(excel_file_path)
        
        if not file_validation['valid']:
            error_msg = f"File validation failed: {file_validation['errors']}"
            raise Exception(error_msg)
        
        # Log warnings if any
        for warning in file_validation.get('warnings', []):
            logger.warning(f"⚠️ {warning}")
            self.pipeline_results['warnings'].append(warning)
        
        logger.info("✅ File structure validation passed")
        return file_validation
    
    def _load_excel_data(self, excel_file_path: str) -> pd.DataFrame:
        """Stage 3: Load Excel data"""
        logger.info("Loading Excel data...")
        
        try:
            df = pd.read_excel(
                excel_file_path,
                sheet_name=self.config['file']['sheet_name'],
                engine='openpyxl',
                na_values=['', ' ', 'NULL', 'null', 'NaN', 'nan', '#N/A']
            )
            
            logger.info(f"✅ Loaded {len(df):,} rows × {len(df.columns)} columns")
            
            # Store in pipeline state for next stages
            self.pipeline_state['raw_data'] = df
            self.pipeline_results['data_flow']['raw_data'] = {
                'rows': len(df),
                'columns': len(df.columns)
            }
            
            return df
            
        except Exception as e:
            raise Exception(f"Excel loading failed: {e}")
    
    def _validate_data_quality(self) -> Dict:
        """Stage 4: Validate data quality"""
        logger.info("Validating data quality...")
        
        df = self.pipeline_state['raw_data']
        data_validation = self.validator.validate_data_quality(df)
        
        if not data_validation['valid']:
            error_msg = f"Data quality validation failed: {data_validation['errors']}"
            raise Exception(error_msg)
        
        # Log warnings
        for warning in data_validation.get('warnings', []):
            logger.warning(f"⚠️ {warning}")
            self.pipeline_results['warnings'].append(warning)
        
        # Log quality score
        quality_score = data_validation.get('data_quality_score', 0)
        logger.info(f"✅ Data quality score: {quality_score:.1f}/100")
        
        return data_validation
    
    def _transform_data(self) -> pd.DataFrame:
        """Stage 5: Transform data"""
        logger.info("Transforming data...")
        
        df = self.pipeline_state['raw_data']
        df_transformed = self.transformer.transform_dataframe(df)
        
        # Get transformation summary
        transform_summary = self.transformer.get_transformation_summary()
        
        # Store transformed data
        self.pipeline_state['transformed_data'] = df_transformed
        self.pipeline_results['data_flow']['transformed_data'] = {
            'rows': len(df_transformed),
            'columns': len(df_transformed.columns),
            'transformation_summary': transform_summary
        }
        
        logger.info(f"✅ Data transformation completed")
        logger.info(f"  Retention rate: {transform_summary['data_quality']['retention_rate']:.1f}%")
        
        return df_transformed
    
    def _load_to_database(self) -> Dict:
        """Stage 6: Load data to database"""
        logger.info("Loading data to database...")
        
        df_transformed = self.pipeline_state['transformed_data']
        load_result = self.db_manager.load_data(df_transformed, method='replace')
        
        if not load_result['success']:
            error_msg = f"Database loading failed: {load_result['errors']}"
            raise Exception(error_msg)
        
        # Log warnings
        for warning in load_result.get('warnings', []):
            logger.warning(f"⚠️ {warning}")
            self.pipeline_results['warnings'].append(warning)
        
        self.pipeline_results['data_flow']['database_load'] = load_result
        
        logger.info(f"✅ Database loading completed: {load_result['rows_inserted']:,} rows")
        return load_result
    
    def _execute_post_load_operations(self) -> Dict:
        """Stage 7: Execute post-load operations"""
        logger.info("Executing post-load operations...")
        
        results = {}
        
        # Create analytical views
        if self.db_manager.create_analytical_views():
            results['analytical_views'] = 'created'
            logger.info("✅ Analytical views created")
        else:
            logger.warning("⚠️ Some analytical views failed to create")
            results['analytical_views'] = 'partial_failure'
        
        return results
    
    def _collect_final_metrics(self) -> Dict:
        """Stage 8: Collect final metrics and validation"""
        logger.info("Collecting final metrics...")
        
        # Get comprehensive data quality metrics
        final_metrics = self.db_manager.get_data_quality_metrics()
        
        # Export sample data for validation
        sample_data = self.db_manager.export_sample_data(limit=10)
        
        self.pipeline_results['final_metrics'] = final_metrics
        
        # Log key metrics
        basic_stats = final_metrics.get('basic_stats', {})
        logger.info(f"✅ Final validation completed")
        logger.info(f"  Total rows: {basic_stats.get('total_rows', 0):,}")
        logger.info(f"  Unique operations: {basic_stats.get('unique_operacoes', 0):,}")
        logger.info(f"  States covered: {basic_stats.get('unique_ufs', 0)}")
        
        return final_metrics
    
    def _finalize_pipeline(self):
        """Finalize pipeline execution"""
        self.pipeline_state['end_time'] = datetime.now()
        self.pipeline_state['total_duration_seconds'] = (
            self.pipeline_state['end_time'] - self.pipeline_state['start_time']
        ).total_seconds()
        
        # Generate final report
        self._generate_pipeline_report()
    
    def _generate_pipeline_report(self):
        """Generate comprehensive pipeline execution report"""
        logger.info("\n" + "="*60)
        logger.info("PIPELINE EXECUTION REPORT")
        logger.info("="*60)
        
        # Overall status
        status = "✅ SUCCESS" if self.pipeline_results['success'] else "❌ FAILED"
        logger.info(f"Status: {status}")
        logger.info(f"Duration: {self.pipeline_state['total_duration_seconds']:.2f} seconds")
        logger.info(f"Stages completed: {len(self.pipeline_state['stages_completed'])}/8")
        
        # Data flow summary
        data_flow = self.pipeline_results.get('data_flow', {})
        if 'raw_data' in data_flow and 'database_load' in data_flow:
            raw_rows = data_flow['raw_data']['rows']
            final_rows = data_flow['database_load']['rows_inserted']
            retention_rate = (final_rows / raw_rows * 100) if raw_rows > 0 else 0
            
            logger.info(f"\nData Flow:")
            logger.info(f"  Input: {raw_rows:,} rows")
            logger.info(f"  Output: {final_rows:,} rows")
            logger.info(f"  Retention: {retention_rate:.1f}%")
        
        # Errors and warnings
        if self.pipeline_results['errors']:
            logger.info(f"\nErrors ({len(self.pipeline_results['errors'])}):")
            for error in self.pipeline_results['errors']:
                logger.info(f"  ❌ {error}")
        
        if self.pipeline_results['warnings']:
            logger.info(f"\nWarnings ({len(self.pipeline_results['warnings'])}):")
            for warning in self.pipeline_results['warnings'][:5]:  # Show first 5
                logger.info(f"  ⚠️ {warning}")
        
        # Final metrics
        final_metrics = self.pipeline_results.get('final_metrics', {})
        if 'basic_stats' in final_metrics:
            stats = final_metrics['basic_stats']
            logger.info(f"\nFinal Database State:")
            logger.info(f"  Total operations: {stats.get('total_rows', 0):,}")
            logger.info(f"  Unique UFs: {stats.get('unique_ufs', 0)}")
            logger.info(f"  Unique repassadores: {stats.get('unique_repassadores', 0)}")
        
        # Next steps
        if self.pipeline_results['success']:
            logger.info(f"\n🎉 Next Steps:")
            logger.info(f"  1. Access dashboard: http://localhost:8507")
            logger.info(f"  2. Query database directly if needed")
            logger.info(f"  3. Check analytical views: vw_novopac_*")
        else:
            logger.info(f"\n🔧 Troubleshooting:")
            logger.info(f"  1. Check error messages above")
            logger.info(f"  2. Verify Excel file format and location")
            logger.info(f"  3. Ensure database is accessible")
        
        logger.info("="*60)
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        log_config = self.config['logging']
        
        # Create logs directory
        log_dir = Path(log_config['log_directory'])
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        log_file = log_dir / f"novopac_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ] if log_config['log_to_console'] else [logging.FileHandler(log_file)]
        )

class ETLPipelineError(Exception):
    """Custom exception for ETL pipeline errors"""
    pass

# Global logger
logger = logging.getLogger(__name__)

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NovoOAC ETL Pipeline')
    parser.add_argument(
        'excel_file', 
        help='Path to Excel file (REUNI_Operações_Novo_PAC_OGU_Interno_CAIXA_21-05-2025.xlsx)'
    )
    parser.add_argument(
        '--config', 
        help='Path to custom config file', 
        default=None
    )
    parser.add_argument(
        '--validate-only', 
        action='store_true',
        help='Only validate data without loading to database'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize ETL orchestrator
        etl = NovoOACETLOrchestrator()
        
        # Run pipeline
        if args.validate_only:
            logger.info("Running in validation-only mode...")
            # TODO: Implement validation-only mode
            result = {'success': False, 'errors': ['Validation-only mode not implemented yet']}
        else:
            result = etl.run_complete_pipeline(args.excel_file)
        
        # Exit with appropriate code
        if result['success']:
            logger.info("🎉 ETL Pipeline completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ ETL Pipeline failed!")
            for error in result['errors']:
                logger.error(f"  Error: {error}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
