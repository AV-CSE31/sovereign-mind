import os
import sys
import json
import urllib.request
import urllib.error

def report_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = 0
    if total_size > 0:
        percent = min(100, int(downloaded / total_size * 100))
        sys.stdout.write(f"\rDownloading: {percent}% ({downloaded / (1024*1024):.1f} MB)")
        sys.stdout.flush()

def download_file(url, dest_path):
    print(f"\nSource: {url}")
    print(f"Destination: {dest_path}")
    try:
        urllib.request.urlretrieve(url, dest_path, report_progress)
        print("\n[OK] Download complete.")
        return True
    except urllib.error.HTTPError as e:
        print(f"\n[ERROR] HTTP Error: {e.code}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Failed: {str(e)}")
        return False

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(root_dir, "launcher.json")
    bin_dir = os.path.join(root_dir, "bin")

    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)

    with open(config_path, "r") as f:
        config = json.load(f)

    # 1. Download Engine
    # 1. Download Engine
    engine_conf = config["engine"]
    
    # Determine filename based on OS
    is_windows = sys.platform == "win32"
    filename = engine_conf["filename"] 
    if not is_windows and filename.endswith(".exe"):
        filename = filename[:-4] # Remove .exe for Linux/Mac

    engine_path = os.path.join(bin_dir, filename)
    
    if not os.path.exists(engine_path):
        print(f"[*] Downloading Inference Engine ({engine_conf['description']})...")
        print(f"    Target: {engine_path}")
        
        if not download_file(engine_conf["url"], engine_path):
            print("[CRITICAL] Failed to download engine.")
            sys.exit(1)
            
        # Make executable on Linux/Mac
        if not is_windows:
            try:
                os.chmod(engine_path, 0o755)
                print("[*] Made engine executable (chmod +x).")
            except Exception as e:
                print(f"[WARN] Failed to set permissions: {e}")

    # 2. Download Model (Try Primary, then Fallbacks)
    model_found = False
    for model in config["models"]:
        model_path = os.path.join(bin_dir, model["filename"])
        if os.path.exists(model_path):
            print(f"[*] Model found: {model['name']}")
            # Create a 'current_model.gguf' symlink or just use this file?
            # Creating a marker file to tell inference engine which model to use involves complexity.
            # Simpler: The Inference Engine will look for ANY .gguf in bin, prioritizing configured ones.
            model_found = True
            break
            
        print(f"[*] Attempting to download: {model['name']} ({model['size_mb']} MB)...")
        if download_file(model["url"], model_path):
             model_found = True
             break
        else:
             print(f"[WARN] Failed to download {model['name']}. Trying next...")

    if not model_found:
        print("[CRITICAL] All model downloads failed. Please check internet connection.")
        sys.exit(1)

if __name__ == "__main__":
    main()
