"""
Pipeline Service
Interface layer between UI and TopStepB pipeline
Manages optimization process launching and monitoring
"""
import subprocess
import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import queue
import logging

# Setup logging
logger = logging.getLogger(__name__)

class PipelineService:
    """Service for managing optimization pipeline execution"""

    def __init__(self):
        self.current_process = None
        self.output_queue = queue.Queue()
        self.project_root = Path(__file__).parent.parent.parent.parent

    def start_optimization(self, config: Dict[str, Any]) -> str:
        """
        Launch optimization process with given configuration

        Args:
            config: Configuration dictionary from UI

        Returns:
            study_name: Unique study name for this optimization

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If process fails to start
        """
        # Validate configuration
        if not config:
            raise ValueError("Configuration is empty")

        # Build study name
        study_name = self._generate_study_name(config)

        # Convert config to command line arguments
        args = self._build_command_args(config)

        # Launch subprocess
        try:
            self._launch_subprocess(args)
            logger.info(f"Optimization launched: {study_name}")
            return study_name
        except Exception as e:
            logger.error(f"Failed to launch optimization: {e}")
            raise RuntimeError(f"Failed to launch optimization: {str(e)}")

    def _generate_study_name(self, config: Dict[str, Any]) -> str:
        """Generate unique study name from configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy = config.get('strategy', 'unknown')
        symbol = config.get('symbol', 'unknown')
        timeframe = config.get('timeframe', 'unknown')

        return f"{strategy}_{symbol}_{timeframe}_{timestamp}"

    def _build_command_args(self, config: Dict[str, Any]) -> list:
        """Build command line arguments from configuration"""
        # Path to main_runner.py
        main_runner = self.project_root / "TopStepB" / "main_runner.py"

        # Build argument list
        args = [
            sys.executable,
            str(main_runner),
            "--strategy", config.get('strategy', 'bollinger_squeeze'),
            "--symbol", config.get('symbol', 'ES'),
            "--timeframe", config.get('timeframe', '5m'),
            "--account-type", config.get('account_type', 'topstep_50k'),
            "--slippage", str(config.get('slippage', 0.25)),
            "--commission", str(config.get('commission', 2.50)),
            "--contracts-per-trade", str(config.get('contracts_per_trade', 1)),
            "--split-type", config.get('split_type', 'walk_forward'),
        ]

        # Optional: split ratios
        if config.get('split_ratios'):
            args.extend(["--split-ratios", config['split_ratios']])

        # Optional: gap days
        if config.get('gap_days') is not None:
            args.extend(["--gap-days", str(config['gap_days'])])

        # Data source
        if config.get('data_file'):
            args.extend(["--data-file", config['data_file']])
        elif config.get('synthetic_bars'):
            args.extend(["--synthetic-bars", str(config['synthetic_bars'])])
        else:
            # Default to synthetic data
            args.extend(["--synthetic-bars", "5000"])

        # Optimization settings
        args.extend([
            "--max-trials", str(config.get('max_trials', 100)),
            "--max-workers", str(config.get('max_workers', 4)),
            "--memory-per-worker-mb", str(config.get('memory_per_worker_mb', 1500)),
            "--timeout-per-trial", str(config.get('timeout_per_trial', 60)),
            "--results-top-n", str(config.get('results_top_n', 10)),
        ])

        # Optional: validation tests
        if config.get('validation_tests'):
            args.extend(["--validation-tests", config['validation_tests']])

        return args

    def _launch_subprocess(self, args: list):
        """Launch subprocess with given arguments"""
        try:
            # Launch process in background
            self.current_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Start output monitoring thread
            output_thread = threading.Thread(
                target=self._monitor_output,
                args=(self.current_process,),
                daemon=True
            )
            output_thread.start()

        except FileNotFoundError as e:
            raise RuntimeError(f"Python executable or main_runner.py not found: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to start process: {e}")

    def _monitor_output(self, process):
        """Monitor process output in background thread"""
        try:
            for line in process.stdout:
                self.output_queue.put(('stdout', line.strip()))

            for line in process.stderr:
                self.output_queue.put(('stderr', line.strip()))
        except Exception as e:
            logger.error(f"Error monitoring output: {e}")

    def stop_optimization(self) -> bool:
        """
        Stop current optimization process gracefully

        Returns:
            success: True if stopped successfully
        """
        if not self.current_process:
            return False

        try:
            self.current_process.terminate()
            self.current_process.wait(timeout=10)
            self.current_process = None
            logger.info("Optimization stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop optimization: {e}")
            # Force kill if needed
            try:
                self.current_process.kill()
                self.current_process = None
                return True
            except:
                return False

    def is_running(self) -> bool:
        """Check if optimization is currently running"""
        if not self.current_process:
            return False

        return self.current_process.poll() is None

    def get_process_output(self, timeout: float = 0.1) -> list:
        """
        Get recent process output

        Args:
            timeout: How long to wait for output

        Returns:
            List of (stream, line) tuples
        """
        output = []
        try:
            while True:
                item = self.output_queue.get(timeout=timeout)
                output.append(item)
        except queue.Empty:
            pass

        return output
