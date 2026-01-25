"""
Local Inference Engine Wrapper.

This module manages the local Llamafile sub-process, providing a standard
OpenAI-compatible interface for the rest of the application.

It handles:
1. Auto-starting the llamafile binary if not running.
2. Hardware detection (not implemented in MVP, defaults to CPU).
3. Health checks.
"""

import subprocess
import time
import httpx
from pathlib import Path
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

class LocalInferenceEngine:
    """Manages the local Llamafile process."""
    
    def __init__(self, binary_path: str = None):
        if binary_path is None:
             import sys
             filename = "llamafile.exe" if sys.platform == "win32" else "llamafile"
             binary_path = f"./bin/{filename}"
        
        self.binary_path = Path(binary_path)
        self.process = None
        self.base_url = "http://localhost:8080/v1" # Standard Llamafile port
        
    def is_running(self) -> bool:
        """Check if the inference server is responding."""
        try:
             # Llamafile exposes /health or just check /v1/models
             response = httpx.get(f"{self.base_url}/models", timeout=2.0)
             return response.status_code == 200
        except Exception:
            return False

    def start(self):
        """Start the local inference server."""
        if self.is_running():
            logger.info("inference_engine_already_running")
            return

        # Check for Llamafile Engine
        engine_path = self.binary_path # Default ./bin/llamafile.exe
        
        # Check for Model (GGUF or Embedded Llamafile)
        # 1. Is the engine itself an embedded llamafile? (Old behavior)
        # If it's seemingly just "llamafile.exe" (small), we need a model.
        # If it's "TinyLlama...llamafile" (big), it's embedded.
        
        # Simplified logic: Look for any .gguf in ./bin
        bin_dir = self.binary_path.parent
        gguf_files = list(bin_dir.glob("*.gguf"))
        
        cmd = [str(self.binary_path), "--server", "--nobrowser", "--host", "0.0.0.0", "--port", "8080"]
        
        if gguf_files:
            # Separate Engine + Model mode
            model_path = gguf_files[0]
            logger.info("found_gguf_model", model=model_path.name)
            cmd.extend(["-m", str(model_path)])
        else:
            # Embedded mode or fail?
            # If no GGUF, we assume binary_path IS the model (old behavior)
            logger.info("no_gguf_found_assuming_embedded_exe")
        
        if not engine_path.exists():
             logger.error("inference_binary_not_found", path=str(engine_path))
             return

        logger.info("starting_inference_engine", cmd=cmd)
        
        # Start detached process
        # Note: We use -ngl 999 to offload all layers to GPU if available (auto-detected by llamafile)
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for startup
        retries = 20
        while retries > 0:
            if self.is_running():
                logger.info("inference_engine_started")
                return
            time.sleep(1)
            retries -= 1
            
        logger.error("inference_engine_startup_timeout")

    def stop(self):
        """Stop the inference server."""
        if self.process:
            self.process.terminate()
            self.process = None

# Singleton
_engine = None

def get_inference_engine() -> LocalInferenceEngine:
    global _engine
    if _engine is None:
        _engine = LocalInferenceEngine()
    return _engine
