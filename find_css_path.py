with open("all_files_legacy.txt", "r") as f:
    for line in f:
        if "components.css" in line:
            print(line.strip())
