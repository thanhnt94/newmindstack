try:
    with open("all_files_legacy.txt", "r", encoding="utf-16") as f:
        print("Opened as UTF-16")
        for line in f:
            if "components.css" in line:
                print("FOUND: " + line.strip())
except:
    try:
        with open("all_files_legacy.txt", "r", encoding="utf-8") as f:
            print("Opened as UTF-8")
            for line in f:
                if "components.css" in line:
                    print("FOUND: " + line.strip())
    except Exception as e:
        print(f"Error: {e}")
