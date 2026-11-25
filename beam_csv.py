import csv
from pathlib import Path


CSV_HEADERS = (
    "x (ft)",
    "shear V (kips)",
    "moment M (kip-ft)",
    "deflection y (in)",
)


def write_analysis_csv(path, analysis):
    columns = (analysis.xs, analysis.shear, analysis.moment, analysis.deflection)
    if any(len(column) != len(analysis.xs) for column in columns[1:]):
        raise ValueError("Analysis data arrays must have matching lengths.")

    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADERS)
        writer.writerows(zip(*columns))
