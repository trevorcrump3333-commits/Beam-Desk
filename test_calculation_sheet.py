import tempfile
import unittest
from pathlib import Path

from beam_calculations import BeamModel, PointLoad, UniformLoad, calculate
from calculation_sheet import export_calculation_sheet


class CalculationSheetTests(unittest.TestCase):
    def test_pdf_contains_inputs_diagrams_and_design_checks(self):
        model = BeamModel(
            support="simply-supported",
            span=20,
            material="Steel",
            section="W12x26",
            deflection_limit="L/360",
            point_loads=[PointLoad(10, 5)],
            uniform_loads=[UniformLoad(0.5, 0, 20)],
        )
        analysis = calculate(model)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calculation-sheet.pdf"
            export_calculation_sheet(path, model, analysis)
            content = path.read_bytes()

        self.assertTrue(content.startswith(b"%PDF-1.4"))
        self.assertTrue(content.endswith(b"%%EOF\n"))
        for expected_text in (
            b"BEAM DESIGN CALCULATION SHEET",
            b"BEAM INPUTS",
            b"Steel / W12x26",
            b"SHEAR DIAGRAM",
            b"MOMENT DIAGRAM",
            b"DEFLECTION DIAGRAM",
            b"BENDING CHECK",
            b"DEFLECTION CHECK",
        ):
            self.assertIn(expected_text, content)

    def test_long_load_schedule_is_included_on_continuation_page(self):
        model = BeamModel(
            span=12,
            material="Steel",
            section="W12x26",
            point_loads=[PointLoad(1, float(position)) for position in range(1, 8)],
        )
        analysis = calculate(model)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calculation-sheet.pdf"
            export_calculation_sheet(path, model, analysis)
            content = path.read_bytes()

        self.assertIn(b"/Count 2", content)
        self.assertIn(b"BEAM INPUTS - LOAD SCHEDULE", content)
        self.assertIn(b"(7.) Tj", content)
        self.assertIn(b"(Point: 1 k at 7 ft) Tj", content)


if __name__ == "__main__":
    unittest.main()
