
    def restart_app(self) -> str:
        """Restart the application."""
        try:
            import sys
            import os
            import subprocess
            
            # Get the current executable and script path
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                executable = sys.executable
                args = [executable]
            else:
                # Running as Python script
                executable = sys.executable
                main_script = os.path.join(os.path.dirname(__file__), '..', 'main.py')
                main_script = os.path.abspath(main_script)
                args = [executable, main_script]
            
            # Start new process and exit current one
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
            
            # Schedule exit after response
            import threading
            def exit_app():
                import time
                time.sleep(1)
                os._exit(0)
            
            threading.Thread(target=exit_app, daemon=True).start()
            
            return json.dumps({"success": True})
            
        except Exception as e:
            return json.dumps({"success": False, "error": f"재시작 실패: {str(e)}"})
