import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime

class ApiSaveImage:
    def save_image(self, base64_data: str, filename: str) -> str:
        """Save base64-encoded image and return base64 data URI for preview.
        
        Args:
            base64_data: Base64-encoded image data (data:image/...;base64,...)
            filename: Original filename
            
        Returns:
            JSON string with base64 data URI for immediate preview.
        """
        try:
            import base64
            
            # Parse base64 data
            if ',' in base64_data:
                header, data = base64_data.split(',', 1)
            else:
                data = base64_data
                header = ""
            
            # Determine file extension from header or original filename
            ext = Path(filename).suffix.lower()
            mime_type = "image/png"
            if not ext:
                # Try to extract from header
                if 'image/png' in header:
                    ext = '.png'
                    mime_type = "image/png"
                elif 'image/jpeg' in header or 'image/jpg' in header:
                    ext = '.jpg'
                    mime_type = "image/jpeg"
                elif 'image/gif' in header:
                    ext = '.gif'
                    mime_type = "image/gif"
                elif 'image/webp' in header:
                    ext = '.webp'
                    mime_type = "image/webp"
                else:
                    ext = '.png'
                    mime_type = "image/png"
            else:
                # Map extension to mime type
                ext_to_mime = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }
                mime_type = ext_to_mime.get(ext, 'image/png')
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]
            safe_name = f"img_{timestamp}{ext}"
            
            # Determine assets directory path
            if hasattr(self, '_storage_path') and self._storage_path:
                assets_dir = Path(self._storage_path) / "assets"
            elif hasattr(self, 'file_storage') and self.file_storage:
                assets_dir = Path(self.file_storage.base_path) / "assets"
            else:
                assets_dir = Path.home() / "NuniMemo" / "assets"
            
            # Ensure assets directory exists
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            # Full path for saving
            image_path = assets_dir / safe_name
            
            # Decode and save
            image_bytes = base64.b64decode(data)
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
                f.flush()  # Ensure file is written to disk immediately
                os.fsync(f.fileno())  # Force write to disk
            
            # Return base64 data URI for immediate preview
            # This ensures the image displays immediately without needing file serving
            data_uri = f"data:{mime_type};base64,{data}"
            
            print(f"DEBUG: Returning data_uri: {data_uri[:50]}...")
            print(f"DEBUG: Returning path: assets/{safe_name}")
            
            return json.dumps({
                "success": True,
                "data": {
                    "data_uri": data_uri,
                    "path": f"assets/{safe_name}",
                    "relative_path": f"assets/{safe_name}",
                    "filename": safe_name
                }
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
