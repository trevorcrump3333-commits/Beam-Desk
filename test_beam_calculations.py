import unittest

from beam_calculations import (
    BeamModel,
    PointLoad,
    UniformLoad,
    calculate,
)


class BeamCalculationTests(unittest.TestCase):
    def test_uniformly_loaded_simply_supported_beam(self):
        model = BeamModel(
            span=20,
            support="simply-supported",
            material="Steel",
            section="W12x26",
            deflection_limit="L/360",
            uniform_loads=[UniformLoad(1.0, 0.0, 20.0)],
        )
        result = calculate(model)
        self.assertAlmostEqual(result.reactions[0], 10.0, places=6)
        self.assertAlmostEqual(result.reactions[1], 10.0, places=6)
        self.assertAlmostEqual(result.max_moment, 50.0, places=3)
        self.assertAlmostEqual(result.bending_stress, 17.96, places=2)
        self.assertTrue(result.bending_pass)
        self.assertTrue(result.deflection_pass)

    def test_point_load_simply_supported_beam(self):
        model = BeamModel(
            span=20,
            support="simply-supported",
            material="Steel",
            section="W12x26",
            deflection_limit="L/360",
            point_loads=[PointLoad(10.0, 5.0)],
        )
        result = calculate(model)
        self.assertAlmostEqual(result.reactions[0], 7.5, places=6)
        self.assertAlmostEqual(result.reactions[1], 2.5, places=6)
        self.assertAlmostEqual(result.max_moment, 37.5, places=3)
        self.assertAlmostEqual(result.bending_stress, 13.47, places=2)

    def test_cantilever_point_load(self):
        model = BeamModel(
            span=10,
            support="cantilever",
            material="Steel",
            section="W12x26",
            deflection_limit="L/360",
            point_loads=[PointLoad(5.0, 10.0)],
        )
        result = calculate(model)
        self.assertAlmostEqual(result.reactions[0], -5.0, places=6)
        self.assertAlmostEqual(result.max_moment, 50.0, places=3)
        self.assertAlmostEqual(result.max_deflection, 0.487, places=2)
        self.assertFalse(result.deflection_pass)

    def test_wood_joist(self):
        model = BeamModel(
            span=12,
            support="simply-supported",
            material="Douglas Fir-Larch",
            section="2x10",
            deflection_limit="L/360",
            uniform_loads=[UniformLoad(0.05, 0.0, 12.0)],
        )
        result = calculate(model)
        self.assertAlmostEqual(result.max_moment, 0.9, places=3)
        self.assertAlmostEqual(result.bending_stress, 0.505, places=2)
        self.assertTrue(result.bending_pass)
        self.assertTrue(result.deflection_pass)


if __name__ == "__main__":
    unittest.main()
