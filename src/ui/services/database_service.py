"""
Database Service
PostgreSQL interface for Optuna studies and trials
"""
import psycopg2
from psycopg2 import pool
import pandas as pd
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

class StorageConfig:
    """Simple storage configuration for UI"""
    def __init__(self):
        self.host = "localhost"
        self.port = 5433
        self.database = "optuna_optimization"
        self.username = "postgres"
        self.password = "AdminAdmin"

class DatabaseService:
    """PostgreSQL interface for Optuna studies"""

    def __init__(self):
        self.config = StorageConfig()
        self.connection_pool = None
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
        except Exception as e:
            print(f"Failed to initialize connection pool: {e}")
            self.connection_pool = None

    def get_connection(self):
        """Get connection from pool"""
        if not self.connection_pool:
            raise ConnectionError("Connection pool not initialized")
        return self.connection_pool.getconn()

    def return_connection(self, conn):
        """Return connection to pool"""
        if self.connection_pool:
            self.connection_pool.putconn(conn)

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            self.return_connection(conn)
            return True
        except Exception:
            return False

    def list_studies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all Optuna studies"""
        try:
            conn = self.get_connection()
            query = """
                SELECT study_id, study_name
                FROM studies
                ORDER BY study_id DESC
                LIMIT %s
            """
            df = pd.read_sql_query(query, conn, params=(limit,))
            self.return_connection(conn)
            return df.to_dict('records')
        except Exception as e:
            print(f"Error listing studies: {e}")
            return []

    def get_study_trials(self, study_name: str) -> pd.DataFrame:
        """Get all trials for a study"""
        try:
            conn = self.get_connection()
            query = """
                SELECT t.trial_id, t.number, t.state, tv.value, t.datetime_start, t.datetime_complete,
                       s.study_name
                FROM trials t
                JOIN studies s ON t.study_id = s.study_id
                LEFT JOIN trial_values tv ON t.trial_id = tv.trial_id
                WHERE s.study_name = %s
                ORDER BY t.number DESC
            """
            df = pd.read_sql_query(query, conn, params=(study_name,))
            self.return_connection(conn)
            return df
        except Exception as e:
            print(f"Error getting trials: {e}")
            return pd.DataFrame()

    def get_study_progress(self, study_name: str) -> Optional[Dict[str, Any]]:
        """Get current progress of a study"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            # Get study ID
            cur.execute("SELECT study_id FROM studies WHERE study_name = %s", (study_name,))
            result = cur.fetchone()
            if not result:
                return None

            study_id = result[0]

            # Get trial counts
            cur.execute("""
                SELECT
                    COUNT(*) as total_trials,
                    SUM(CASE WHEN t.state = 'COMPLETE' THEN 1 ELSE 0 END) as completed_trials,
                    SUM(CASE WHEN t.state = 'RUNNING' THEN 1 ELSE 0 END) as running_trials,
                    SUM(CASE WHEN t.state = 'PRUNED' THEN 1 ELSE 0 END) as pruned_trials,
                    MAX(tv.value) as best_value
                FROM trials t
                LEFT JOIN trial_values tv ON t.trial_id = tv.trial_id
                WHERE t.study_id = %s
            """, (study_id,))

            result = cur.fetchone()
            cur.close()
            self.return_connection(conn)

            if result:
                return {
                    'total_trials': result[0] or 0,
                    'completed_trials': result[1] or 0,
                    'running_trials': result[2] or 0,
                    'pruned_trials': result[3] or 0,
                    'best_value': result[4]
                }

            return None

        except Exception as e:
            print(f"Error getting study progress: {e}")
            return None

    def get_best_trial(self, study_name: str) -> Optional[Dict[str, Any]]:
        """Get best trial from a study"""
        try:
            conn = self.get_connection()
            query = """
                SELECT t.trial_id, t.number, tv.value, t.state, t.datetime_complete
                FROM trials t
                JOIN studies s ON t.study_id = s.study_id
                LEFT JOIN trial_values tv ON t.trial_id = tv.trial_id
                WHERE s.study_name = %s AND t.state = 'COMPLETE'
                ORDER BY tv.value DESC
                LIMIT 1
            """
            df = pd.read_sql_query(query, conn, params=(study_name,))
            self.return_connection(conn)

            if not df.empty:
                return df.iloc[0].to_dict()
            return None

        except Exception as e:
            print(f"Error getting best trial: {e}")
            return None

    def delete_study(self, study_name: str) -> bool:
        """Delete a study and all its trials"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()

            # Get study ID
            cur.execute("SELECT study_id FROM studies WHERE study_name = %s", (study_name,))
            result = cur.fetchone()
            if not result:
                return False

            study_id = result[0]

            # Delete trials first (foreign key constraint)
            cur.execute("DELETE FROM trial_params WHERE trial_id IN (SELECT trial_id FROM trials WHERE study_id = %s)", (study_id,))
            cur.execute("DELETE FROM trial_values WHERE trial_id IN (SELECT trial_id FROM trials WHERE study_id = %s)", (study_id,))
            cur.execute("DELETE FROM trials WHERE study_id = %s", (study_id,))
            cur.execute("DELETE FROM studies WHERE study_id = %s", (study_id,))

            conn.commit()
            cur.close()
            self.return_connection(conn)
            return True

        except Exception as e:
            print(f"Error deleting study: {e}")
            return False

    def get_trial_parameters(self, study_name: str, trial_number: int) -> Dict[str, Any]:
        """Get parameters for a specific trial"""
        try:
            conn = self.get_connection()
            query = """
                SELECT tp.param_name, tp.param_value
                FROM trial_params tp
                JOIN trials t ON tp.trial_id = t.trial_id
                JOIN studies s ON t.study_id = s.study_id
                WHERE s.study_name = %s AND t.number = %s
                ORDER BY tp.param_name
            """
            df = pd.read_sql_query(query, conn, params=(study_name, trial_number))
            self.return_connection(conn)

            if not df.empty:
                return dict(zip(df['param_name'], df['param_value']))
            return {}
        except Exception as e:
            print(f"Error getting trial parameters: {e}")
            return {}

    def get_trial_metrics(self, study_name: str, trial_number: int) -> Dict[str, Any]:
        """Get all performance metrics for a specific trial"""
        try:
            conn = self.get_connection()
            query = """
                SELECT key, value_json
                FROM trial_user_attributes
                JOIN trials t ON trial_user_attributes.trial_id = t.trial_id
                JOIN studies s ON t.study_id = s.study_id
                WHERE s.study_name = %s AND t.number = %s AND key LIKE 'metric_%%'
            """
            df = pd.read_sql_query(query, conn, params=(study_name, trial_number))
            self.return_connection(conn)

            import json
            metrics = {}
            for _, row in df.iterrows():
                key = row['key']
                value_json = row['value_json']
                metric_name = key.replace('metric_', '')

                # Skip aggregated statistics (_mean, _std, _min, _max)
                if any(suffix in metric_name for suffix in ['_mean', '_std', '_min', '_max']):
                    continue

                # Parse JSON value
                try:
                    metrics[metric_name] = json.loads(value_json)
                except:
                    metrics[metric_name] = value_json

            # Map metric names for UI compatibility
            if 'total_trades' in metrics:
                metrics['num_trades'] = metrics['total_trades']
            if 'total_dollar_pnl' in metrics:
                metrics['total_pnl'] = metrics['total_dollar_pnl']

            return metrics

        except Exception as e:
            print(f"Error getting trial metrics: {e}")
            return {}

    def get_best_trial_with_metrics(self, study_name: str) -> Optional[Dict[str, Any]]:
        """Get best trial with all its metrics"""
        try:
            # First get the best trial
            best_trial = self.get_best_trial(study_name)
            if not best_trial:
                return None

            # Get metrics for this trial
            trial_number = best_trial['number']
            metrics = self.get_trial_metrics(study_name, trial_number)

            # Merge trial info and metrics
            result = best_trial.copy()
            result['metrics'] = metrics

            return result

        except Exception as e:
            print(f"Error getting best trial with metrics: {e}")
            return None

    def __del__(self):
        """Clean up connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
