import tempfile
import unittest
from pathlib import Path

from beam_calculations import BeamModel, PointLoad, UniformLoad
from beam_files import data_to_model, open_beam_file, save_beam_file


class BeamFileTests(unittest.TestCase):
    def test_save_and_open_preserves_all_beam_settings_and_loads(self):
        model = BeamModel(
            support="cantilever",
            span=14.5,
            material="Douglas Fir-Larch",
            section="2x12",
            deflection_limit="L/240",
            point_loads=[PointLoad(2.5, 6.25), PointLoad(1.0, 14.5)],
            uniform_loads=[UniformLoad(0.35, 1.5, 12.0)],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "design.beam.json"
            save_beam_file(path, model)
            loaded = open_beam_file(path)

        self.assertEqual(loaded.support, model.support)
        self.assertEqual(loaded.span, model.span)
        self.assertEqual(loaded.material, model.material)
        self.assertEqual(loaded.section, model.section)
        self.assertEqual(loaded.deflection_limit, model.deflection_limit)
        self.assertEqual(loaded.point_loads, model.point_loads)
        self.assertEqual(loaded.uniform_loads, model.uniform_loads)

    def test_rejects_load_position_outside_span(self):
        data = {
            "format": "beam-designer",
            "version": 1,
            "beam": {
                "support": "simply-supported",
                "span": 12,
                "material": "Steel",
                "section": "W12x26",
                "deflection_limit": "L/360",
                "point_loads": [{"magnitude": 1, "position": 12.5}],
                "uniform_loads": [],
            },
        }
        with self.assertRaisesRegex(ValueError, "within the beam span"):
            data_to_model(data)


if __name__ == "__main__":
    unittest.main()
