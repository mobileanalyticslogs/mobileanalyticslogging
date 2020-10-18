
with open("CSV_PATH", "r") as f:
    lines = f.readlines()
    for line in lines:
        if "LOG_ADDED" in line or "LOG_DELETED" in line:
            new_line = line[:-1]

            print(new_line)