import csv
import tempfile
import unittest
from pathlib import Path

from beam_calculations import BeamModel, UniformLoad, calculate
from beam_csv import CSV_HEADERS, write_analysis_csv


class BeamCsvTests(unittest.TestCase):
    def test_export_writes_sampled_x_shear_moment_and_deflection(self):
        model = BeamModel(
            span=4,
            support="simply-supported",
            material="Steel",
            section="W12x26",
            uniform_loads=[UniformLoad(1.0, 0.0, 4.0)],
        )
        analysis = calculate(model)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analysis.csv"
            write_analysis_csv(path, analysis)
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))

        self.assertEqual(tuple(rows[0]), CSV_HEADERS)
        self.assertEqual(len(rows) - 1, len(analysis.xs))
        first = [float(value) for value in rows[1]]
        last = [float(value) for value in rows[-1]]
        self.assertEqual(first, [analysis.xs[0], analysis.shear[0], analysis.moment[0], analysis.deflection[0]])
        self.assertEqual(last, [analysis.xs[-1], analysis.shear[-1], analysis.moment[-1], analysis.deflection[-1]])


if __name__ == "__main__":
    unittest.main()
