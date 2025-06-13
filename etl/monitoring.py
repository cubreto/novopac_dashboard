#!/usr/bin/env python3
"""
NovoOAC ETL Monitoring
Comprehensive monitoring, alerting, and metrics collection for ETL pipeline
"""

import logging
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class ETLMonitor:
    """Monitors ETL pipeline execution and provides alerting"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.monitoring_config = self.config.get('monitoring', {})
        
        # Alert thresholds
        self.thresholds = {
            'min_rows_processed': 4000,  # Expect at least 4K rows
            'max_processing_time_minutes': 15,  # Max 15 minutes for 4,899 rows
            'max_memory_usage_mb': 2048,  # Max 2GB memory
            'min_data_quality_score': 80.0,  # Min quality score
            'max_error_rate': 0.05,  # Max 5% error rate
            'max_null_rate_increase': 10.0  # Max 10% increase in nulls
        }
        
        # Historical data storage
        self.metrics_file = Path(self.monitoring_config.get('metrics_file', 'etl_logs/etl_metrics.json'))
        self.metrics_file.parent.mkdir(exist_ok=True)
        
        # Current run metrics
        self.current_metrics = {
            'run_id': self._generate_run_id(),
            'start_time': None,
            'end_time': None,
            'pipeline_result': None,
            'performance_metrics': {},
            'data_quality_metrics': {},
            'alerts_triggered': []
        }
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID"""
        return f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def start_monitoring(self):
        """Start monitoring a new ETL run"""
        self.current_metrics['start_time'] = datetime.now()
        logger.info(f"📊 ETL Monitoring started: {self.current_metrics['run_id']}")
    
    def record_pipeline_result(self, pipeline_result: Dict):
        """Record the complete pipeline execution result"""
        self.current_metrics['end_time'] = datetime.now()
        self.current_metrics['pipeline_result'] = pipeline_result
        
        # Calculate performance metrics
        self._calculate_performance_metrics(pipeline_result)
        
        # Extract data quality metrics
        self._extract_data_quality_metrics(pipeline_result)
        
        # Check for alert conditions
        self._check_alert_conditions()
        
        # Save metrics to file
        self._save_metrics()
        
        # Send alerts if needed
        self._send_alerts_if_needed()
        
        logger.info(f"📊 ETL Monitoring completed: {self.current_metrics['run_id']}")
    
    def _calculate_performance_metrics(self, pipeline_result: Dict):
        """Calculate performance metrics from pipeline result"""
        start_time = self.current_metrics['start_time']
        end_time = self.current_metrics['end_time']
        
        total_duration = (end_time - start_time).total_seconds()
        
        # Basic performance metrics
        performance = {
            'total_duration_seconds': total_duration,
            'total_duration_minutes': total_duration / 60,
            'success': pipeline_result.get('success', False),
            'stages_completed': len(pipeline_result.get('stages', {})),
            'errors_count': len(pipeline_result.get('errors', [])),
            'warnings_count': len(pipeline_result.get('warnings', []))
        }
        
        # Data throughput metrics
        data_flow = pipeline_result.get('data_flow', {})
        if 'database_load' in data_flow:
            db_load = data_flow['database_load']
            rows_processed = db_load.get('rows_inserted', 0)
            
            performance.update({
                'rows_processed': rows_processed,
                'rows_per_second': rows_processed / total_duration if total_duration > 0 else 0,
                'processing_rate_mb_per_minute': (rows_processed * 0.001) / (total_duration / 60) if total_duration > 0 else 0
            })
        
        # Stage timing breakdown
        stage_timings = {}
        for stage_name, stage_result in pipeline_result.get('stages', {}).items():
            stage_timings[stage_name] = {
                'duration_seconds': stage_result.get('duration_seconds', 0),
                'success': stage_result.get('success', False)
            }
        
        performance['stage_timings'] = stage_timings
        
        self.current_metrics['performance_metrics'] = performance
    
    def _extract_data_quality_metrics(self, pipeline_result: Dict):
        """Extract data quality metrics"""
        final_metrics = pipeline_result.get('final_metrics', {})
        
        data_quality = {
            'basic_stats': final_metrics.get('basic_stats', {}),
            'null_analysis': final_metrics.get('null_analysis', {}),
            'categorical_analysis': final_metrics.get('categorical_analysis', {}),
            'financial_analysis': final_metrics.get('financial_analysis', {})
        }
        
        # Calculate data quality score
        data_quality['overall_score'] = self._calculate_data_quality_score(final_metrics)
        
        # Data retention rate
        data_flow = pipeline_result.get('data_flow', {})
        if 'raw_data' in data_flow and 'database_load' in data_flow:
            raw_rows = data_flow['raw_data']['rows']
            final_rows = data_flow['database_load']['rows_inserted']
            data_quality['retention_rate'] = (final_rows / raw_rows * 100) if raw_rows > 0 else 0
        
        self.current_metrics['data_quality_metrics'] = data_quality
    
    def _calculate_data_quality_score(self, metrics: Dict) -> float:
        """Calculate overall data quality score"""
        score = 100.0
        
        # Deduct for low row count
        basic_stats = metrics.get('basic_stats', {})
        total_rows = basic_stats.get('total_rows', 0)
        if total_rows < self.thresholds['min_rows_processed']:
            score -= 20
        
        # Deduct for high null rates (if we have historical comparison)
        # This would require historical data to compare against
        
        # Deduct for missing critical data
        categorical = metrics.get('categorical_analysis', {})
        suspensiva_data = categorical.get('suspensiva', {})
        total_suspensivas = sum(suspensiva_data.values()) if suspensiva_data else 0
        if total_suspensivas < 2000:  # Expect ~2,700 suspensivas
            score -= 10
        
        return max(0.0, score)
    
    def _check_alert_conditions(self):
        """Check for conditions that should trigger alerts"""
        alerts = []
        
        performance = self.current_metrics['performance_metrics']
        data_quality = self.current_metrics['data_quality_metrics']
        
        # Check pipeline success
        if not performance.get('success', False):
            alerts.append({
                'type': 'PIPELINE_FAILURE',
                'severity': 'CRITICAL',
                'message': f"ETL Pipeline failed: {performance.get('errors_count', 0)} errors"
            })
        
        # Check processing time
        duration_minutes = performance.get('total_duration_minutes', 0)
        if duration_minutes > self.thresholds['max_processing_time_minutes']:
            alerts.append({
                'type': 'SLOW_PROCESSING',
                'severity': 'WARNING',
                'message': f"Processing took {duration_minutes:.1f} minutes (threshold: {self.thresholds['max_processing_time_minutes']})"
            })
        
        # Check row count
        rows_processed = performance.get('rows_processed', 0)
        if rows_processed < self.thresholds['min_rows_processed']:
            alerts.append({
                'type': 'LOW_ROW_COUNT',
                'severity': 'WARNING',
                'message': f"Only {rows_processed:,} rows processed (expected >{self.thresholds['min_rows_processed']:,})"
            })
        
        # Check data quality score
        quality_score = data_quality.get('overall_score', 0)
        if quality_score < self.thresholds['min_data_quality_score']:
            alerts.append({
                'type': 'LOW_DATA_QUALITY',
                'severity': 'WARNING',
                'message': f"Data quality score: {quality_score:.1f} (threshold: {self.thresholds['min_data_quality_score']})"
            })
        
        # Check retention rate
        retention_rate = data_quality.get('retention_rate', 100)
        if retention_rate < 95.0:  # Alert if losing more than 5% of data
            alerts.append({
                'type': 'HIGH_DATA_LOSS',
                'severity': 'WARNING',
                'message': f"Data retention rate: {retention_rate:.1f}% (expected >95%)"
            })
        
        self.current_metrics['alerts_triggered'] = alerts
        
        # Log alerts
        for alert in alerts:
            severity = alert['severity']
            message = alert['message']
            if severity == 'CRITICAL':
                logger.error(f"🚨 CRITICAL ALERT: {message}")
            else:
                logger.warning(f"⚠️ WARNING ALERT: {message}")
    
    def _save_metrics(self):
        """Save metrics to JSON file for historical tracking"""
        try:
            # Load existing metrics
            historical_metrics = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    historical_metrics = json.load(f)
            
            # Add current metrics
            metric_record = {
                'run_id': self.current_metrics['run_id'],
                'timestamp': self.current_metrics['start_time'].isoformat(),
                'end_timestamp': self.current_metrics['end_time'].isoformat(),
                'performance': self.current_metrics['performance_metrics'],
                'data_quality': self.current_metrics['data_quality_metrics'],
                'alerts': self.current_metrics['alerts_triggered']
            }
            
            historical_metrics.append(metric_record)
            
            # Keep only last 100 runs to prevent file from growing too large
            if len(historical_metrics) > 100:
                historical_metrics = historical_metrics[-100:]
            
            # Save back to file
            with open(self.metrics_file, 'w') as f:
                json.dump(historical_metrics, f, indent=2, default=str)
            
            logger.info(f"📊 Metrics saved: {self.metrics_file}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _send_alerts_if_needed(self):
        """Send alerts if configured and conditions are met"""
        alerts = self.current_metrics['alerts_triggered']
        
        if not alerts:
            return
        
        # Check if alerting is enabled
        if not self.monitoring_config.get('alert_on_failure', False):
            return
        
        # Filter alerts by severity
        critical_alerts = [a for a in alerts if a['severity'] == 'CRITICAL']
        warning_alerts = [a for a in alerts if a['severity'] == 'WARNING']
        
        # Send critical alerts always, warnings only if configured
        should_send_warnings = self.monitoring_config.get('alert_on_warnings', False)
        
        alerts_to_send = critical_alerts
        if should_send_warnings:
            alerts_to_send.extend(warning_alerts)
        
        if alerts_to_send:
            self._send_alert_notification(alerts_to_send)
    
    def _send_alert_notification(self, alerts: List[Dict]):
        """Send alert notification (placeholder implementation)"""
        # This is a placeholder - in production, you would implement:
        # - Email notifications
        # - Slack/Teams webhook
        # - SMS alerts
        # - Dashboard notifications
        
        logger.warning(f"🚨 ALERT NOTIFICATION: {len(alerts)} alerts triggered")
        for alert in alerts:
            logger.warning(f"  {alert['severity']}: {alert['message']}")
        
        # TODO: Implement actual notification mechanisms
        # Example email implementation (would need SMTP configuration):
        # self._send_email_alert(alerts)
        
        # Example Slack webhook (would need webhook URL):
        # self._send_slack_alert(alerts)
    
    def generate_monitoring_report(self) -> str:
        """Generate a comprehensive monitoring report"""
        if not self.current_metrics['pipeline_result']:
            return "No pipeline result available for reporting"
        
        performance = self.current_metrics['performance_metrics']
        data_quality = self.current_metrics['data_quality_metrics']
        alerts = self.current_metrics['alerts_triggered']
        
        report_lines = [
            "="*60,
            "ETL PIPELINE MONITORING REPORT",
            "="*60,
            f"Run ID: {self.current_metrics['run_id']}",
            f"Start Time: {self.current_metrics['start_time']}",
            f"End Time: {self.current_metrics['end_time']}",
            f"Duration: {performance.get('total_duration_minutes', 0):.2f} minutes",
            "",
            "PERFORMANCE METRICS:",
            f"  Success: {'✅ YES' if performance.get('success') else '❌ NO'}",
            f"  Rows Processed: {performance.get('rows_processed', 0):,}",
            f"  Processing Rate: {performance.get('rows_per_second', 0):.1f} rows/second",
            f"  Stages Completed: {performance.get('stages_completed', 0)}",
            f"  Errors: {performance.get('errors_count', 0)}",
            f"  Warnings: {performance.get('warnings_count', 0)}",
            "",
            "DATA QUALITY METRICS:",
            f"  Overall Score: {data_quality.get('overall_score', 0):.1f}/100",
            f"  Data Retention: {data_quality.get('retention_rate', 0):.1f}%",
        ]
        
        # Add basic statistics
        basic_stats = data_quality.get('basic_stats', {})
        if basic_stats:
            report_lines.extend([
                f"  Total Rows: {basic_stats.get('total_rows', 0):,}",
                f"  Unique Operations: {basic_stats.get('unique_operacoes', 0):,}",
                f"  States (UF): {basic_stats.get('unique_ufs', 0)}",
                f"  Repassadores: {basic_stats.get('unique_repassadores', 0)}",
            ])
        
        # Add alerts section
        if alerts:
            report_lines.extend([
                "",
                "ALERTS TRIGGERED:",
            ])
            for alert in alerts:
                icon = "🚨" if alert['severity'] == 'CRITICAL' else "⚠️"
                report_lines.append(f"  {icon} {alert['severity']}: {alert['message']}")
        else:
            report_lines.extend([
                "",
                "ALERTS: ✅ No alerts triggered"
            ])
        
        # Add stage timing breakdown
        stage_timings = performance.get('stage_timings', {})
        if stage_timings:
            report_lines.extend([
                "",
                "STAGE PERFORMANCE:"
            ])
            for stage_name, timing in stage_timings.items():
                status = "✅" if timing.get('success') else "❌"
                duration = timing.get('duration_seconds', 0)
                report_lines.append(f"  {status} {stage_name}: {duration:.2f}s")
        
        report_lines.append("="*60)
        
        return "\n".join(report_lines)
    
    def get_historical_metrics(self, days: int = 30) -> List[Dict]:
        """Get historical metrics for trend analysis"""
        try:
            if not self.metrics_file.exists():
                return []
            
            with open(self.metrics_file, 'r') as f:
                all_metrics = json.load(f)
            
            # Filter by date range
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_metrics = []
            
            for metric in all_metrics:
                metric_date = datetime.fromisoformat(metric['timestamp'])
                if metric_date >= cutoff_date:
                    recent_metrics.append(metric)
            
            return recent_metrics
            
        except Exception as e:
            logger.error(f"Failed to load historical metrics: {e}")
            return []
    
    def export_metrics_csv(self, output_file: str = None) -> str:
        """Export metrics to CSV for analysis"""
        if not output_file:
            output_file = f"etl_metrics_{datetime.now().strftime('%Y%m%d')}.csv"
        
        try:
            historical_metrics = self.get_historical_metrics(days=90)
            
            if not historical_metrics:
                logger.warning("No historical metrics available for export")
                return output_file
            
            # Prepare CSV data
            csv_rows = []
            for metric in historical_metrics:
                performance = metric.get('performance', {})
                data_quality = metric.get('data_quality', {})
                
                row = {
                    'run_id': metric.get('run_id'),
                    'timestamp': metric.get('timestamp'),
                    'duration_minutes': performance.get('total_duration_minutes'),
                    'success': performance.get('success'),
                    'rows_processed': performance.get('rows_processed'),
                    'rows_per_second': performance.get('rows_per_second'),
                    'errors_count': performance.get('errors_count'),
                    'warnings_count': performance.get('warnings_count'),
                    'data_quality_score': data_quality.get('overall_score'),
                    'retention_rate': data_quality.get('retention_rate'),
                    'alerts_count': len(metric.get('alerts', []))
                }
                csv_rows.append(row)
            
            # Write CSV
            with open(output_file, 'w', newline='') as csvfile:
                if csv_rows:
                    fieldnames = csv_rows[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_rows)
            
            logger.info(f"📊 Metrics exported to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to export metrics CSV: {e}")
            return output_file

# Convenience function for simple monitoring
def monitor_etl_pipeline(pipeline_result: Dict, config: Dict = None) -> Dict:
    """Simple function to monitor an ETL pipeline result"""
    monitor = ETLMonitor(config)
    monitor.start_monitoring()
    monitor.record_pipeline_result(pipeline_result)
    
    return {
        'monitoring_report': monitor.generate_monitoring_report(),
        'alerts_triggered': monitor.current_metrics['alerts_triggered'],
        'metrics_saved': monitor.metrics_file.exists()
    }

if __name__ == "__main__":
    # Test monitoring with sample data
    print("NovoOAC ETL Monitoring Test")
    print("="*40)
    
    # Sample pipeline result for testing
    sample_result = {
        'success': True,
        'stages': {
            'data_loading': {'success': True, 'duration_seconds': 5.2},
            'data_transformation': {'success': True, 'duration_seconds': 12.8},
            'database_loading': {'success': True, 'duration_seconds': 8.1}
        },
        'data_flow': {
            'raw_data': {'rows': 4899, 'columns': 78},
            'database_load': {'rows_inserted': 4895, 'success': True}
        },
        'final_metrics': {
            'basic_stats': {
                'total_rows': 4895,
                'unique_operacoes': 4805,
                'unique_ufs': 27,
                'unique_repassadores': 6
            }
        },
        'errors': [],
        'warnings': ['Sample warning message']
    }
    
    # Test monitoring
    monitor_result = monitor_etl_pipeline(sample_result)
    print("Monitoring test completed:")
    print(f"Alerts: {len(monitor_result['alerts_triggered'])}")
    print(f"Metrics saved: {monitor_result['metrics_saved']}")
