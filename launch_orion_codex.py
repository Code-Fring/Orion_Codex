import os
import sys
import subprocess
import time
import threading
import signal
import atexit
import webbrowser
from pathlib import Path

class OrionCodexLauncher:
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.backend_port = 8000
        self.frontend_port = 3000
        self.backend_process = None
        self.frontend_process = None
        self.running = False
        
    def check_prerequisites(self):
        """Check if Python and Node.js are available"""
        print("🔍 Checking prerequisites...")
        
        # Check Python
        try:
            result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
            print(f"✓ Python: {result.stdout.strip()}")
        except Exception as e:
            print(f"✗ Python not found: {e}")
            return False
            
        # Check Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            print(f"✓ Node.js: {result.stdout.strip()}")
        except Exception as e:
            print(f"✗ Node.js not found: {e}")
            return False
            
        return True
    
    def find_free_port(self, start_port, max_attempts=10):
        """Find a free port starting from start_port"""
        import socket
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        return start_port
    
    def start_backend(self):
        """Start the FastAPI backend"""
        print(f"🚀 Starting backend on port {self.backend_port}...")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)
        
        # Use uvicorn directly
        uvicorn_cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", 
             "--host", "0.0.0.0", "--port", str(self.backend_port)]
        
        self.backend_process = subprocess.Popen(
            uvicorn_cmd,
            cwd=self.project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor backend output in a thread
        def monitor_backend():
            for line in iter(self.backend_process.stdout.readline, ''):
                if line:
                    print(f"[BACKEND] {line.rstrip()}")
        
        threading.Thread(target=monitor_backend, daemon=True).start()
        
        # Wait for backend to be ready
        print("⏳ Waiting for backend to start...")
        for i in range(30):
            try:
                import urllib.request
                response = urllib.request.urlopen(f"http://localhost:{self.backend_port}/health", timeout=2)
                if response.getcode() == 200:
                    print(f"✓ Backend running at http://localhost:{self.backend_port}")
                    return True
            except:
                pass
            time.sleep(1)
            
        print("✗ Backend failed to start")
        return False
    
    def start_frontend(self):
        """Start the Vite frontend"""
        print(f"🚀 Starting frontend on port {self.frontend_port}...")
        
        # Use npm.cmd on Windows
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        self.frontend_process = subprocess.Popen(
            [npm_cmd, "run", "dev", "--", "--host", "0.0.0.0", "--port", str(self.frontend_port)],
            cwd=self.frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor frontend output in a thread
        def monitor_frontend():
            for line in iter(self.frontend_process.stdout.readline, ''):
                if line:
                    print(f"[FRONTEND] {line.rstrip()}")
        
        threading.Thread(target=monitor_frontend, daemon=True).start()
        
        # Wait for frontend to be ready
        print("⏳ Waiting for frontend to start...")
        for i in range(30):
            try:
                import urllib.request
                response = urllib.request.urlopen(f"http://localhost:{self.frontend_port}", timeout=2)
                if response.getcode() == 200:
                    print(f"✓ Frontend running at http://localhost:{self.frontend_port}")
                    return True
            except:
                pass
            time.sleep(1)
            
        print("✗ Frontend failed to start")
        return False
    
    def launch_browser(self):
        """Open the frontend in the default browser"""
        time.sleep(2)
        url = f"http://localhost:{self.frontend_port}"
        print(f"🌐 Opening {url} in browser...")
        webbrowser.open(url)
    
    def cleanup(self):
        """Stop all processes"""
        print("\n🛑 Stopping all services...")
        self.running = False
        
        if self.backend_process:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
                
        if self.frontend_process:
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
                
        print("✓ All services stopped")
    
    def run(self):
        """Main entry point"""
        print("=" * 50)
        print("   Orion Codex Launcher")
        print("   Autonomous Software Engineering Platform")
        print("=" * 50)
        print()
        
        if not self.check_prerequisites():
            input("\nPress Enter to exit...")
            return 1
            
        # Find available ports
        self.backend_port = self.find_free_port(8000)
        self.frontend_port = self.find_free_port(3000)
        
        print(f"📡 Using backend port: {self.backend_port}")
        print(f"📡 Using frontend port: {self.frontend_port}")
        print()
        
        # Start services
        if not self.start_backend():
            self.cleanup()
            input("\nPress Enter to exit...")
            return 1
            
        if not self.start_frontend():
            self.cleanup()
            input("\nPress Enter to exit...")
            return 1
        
        self.running = True
        
        # Launch browser
        threading.Thread(target=self.launch_browser, daemon=True).start()
        
        print()
        print("=" * 50)
        print("   Orion Codex is running!")
        print("=" * 50)
        print(f"Backend:  http://localhost:{self.backend_port}")
        print(f"Frontend: http://localhost:{self.frontend_port}")
        print(f"API Docs: http://localhost:{self.backend_port}/docs")
        print()
        print("Press Ctrl+C to stop all services...")
        print()
        
        # Register cleanup
        atexit.register(self.cleanup)
        
        # Wait for interrupt
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
            
        return 0


def main():
    launcher = OrionCodexLauncher()
    return launcher.run()


if __name__ == "__main__":
    sys.exit(main())