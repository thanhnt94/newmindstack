try:
    from pydub import AudioSegment
    print("pydub imported successfully.")
    # Create silent segment
    silence = AudioSegment.silent(duration=100)
    print("Silent segment created.")
    # Try exporting to mp3 (checks ffmpeg)
    # Use a dummy file path
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        out_path = tmp.name
        
    try:
        silence.export(out_path, format="mp3")
        print("Export to mp3 successful (ffmpeg found).")
    except Exception as e:
        print(f"Export failed: {e}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
            
except ImportError:
    print("pydub not installed.")
except Exception as e:
    print(f"General error: {e}")
