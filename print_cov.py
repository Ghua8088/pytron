import json

with open("coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("cov.txt", "w", encoding="utf-8") as out:
    out.write(f"Total Coverage: {data['totals']['percent_covered']:.2f}%\n\n")
    for file_path, file_data in data["files"].items():
        cov = file_data["summary"]["percent_covered"]
        if cov < 100:
            missing = ", ".join(str(m) for m in file_data["missing_lines"])
            out.write(
                f"{file_path}: {cov:.2f}% (missing lines count: {len(file_data['missing_lines'])})\n"
            )
