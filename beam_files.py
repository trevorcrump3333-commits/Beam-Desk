import json
import math
from pathlib import Path

from beam_calculations import (
    BeamModel,
    PointLoad,
    UniformLoad,
    sections_for,
)


FILE_FORMAT = "beam-designer"
FILE_VERSION = 1


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number." % label)
    if not math.isfinite(value):
        raise ValueError("%s must be finite." % label)
    return float(value)


def model_to_data(model):
    return {
        "format": FILE_FORMAT,
        "version": FILE_VERSION,
        "beam": {
            "support": model.support,
            "span": model.span,
            "material": model.material,
            "section": model.section,
            "deflection_limit": model.deflection_limit,
            "point_loads": [
                {"magnitude": load.magnitude, "position": load.position}
                for load in model.point_loads
            ],
            "uniform_loads": [
                {
                    "magnitude": load.magnitude,
                    "start": load.start,
                    "end": load.end,
                }
                for load in model.uniform_loads
            ],
        },
    }


def data_to_model(data):
    if not isinstance(data, dict):
        raise ValueError("Beam file must contain a JSON object.")
    if data.get("format") != FILE_FORMAT:
        raise ValueError("This is not a Beam Designer file.")
    if data.get("version") != FILE_VERSION:
        raise ValueError("Unsupported Beam Designer file version.")

    beam = data.get("beam")
    if not isinstance(beam, dict):
        raise ValueError("Beam file is missing its beam settings.")

    support = beam.get("support")
    if support not in ("simply-supported", "cantilever"):
        raise ValueError("Support type must be simply-supported or cantilever.")

    span = _number(beam.get("span"), "Span")
    if not 4 <= span <= 40:
        raise ValueError("Span must be between 4 and 40 ft.")

    material = beam.get("material")
    if material not in ("Steel", "Douglas Fir-Larch"):
        raise ValueError("Unrecognized material.")

    section = beam.get("section")
    if section not in {item["name"] for item in sections_for(material)}:
        raise ValueError("Section does not belong to the selected material.")

    deflection_limit = beam.get("deflection_limit")
    if deflection_limit not in ("L/240", "L/360"):
        raise ValueError("Deflection limit must be L/240 or L/360.")

    point_data = beam.get("point_loads")
    if not isinstance(point_data, list):
        raise ValueError("Point loads must be a list.")
    point_loads = []
    for index, item in enumerate(point_data, start=1):
        if not isinstance(item, dict):
            raise ValueError("Point load %d must be an object." % index)
        magnitude = _number(item.get("magnitude"), "Point load %d magnitude" % index)
        position = _number(item.get("position"), "Point load %d position" % index)
        if magnitude < 0:
            raise ValueError("Point load magnitudes cannot be negative.")
        if not 0 <= position <= span:
            raise ValueError("Point load positions must be within the beam span.")
        point_loads.append(PointLoad(magnitude, position))

    uniform_data = beam.get("uniform_loads")
    if not isinstance(uniform_data, list):
        raise ValueError("Uniform loads must be a list.")
    uniform_loads = []
    for index, item in enumerate(uniform_data, start=1):
        if not isinstance(item, dict):
            raise ValueError("Uniform load %d must be an object." % index)
        magnitude = _number(item.get("magnitude"), "Uniform load %d magnitude" % index)
        start = _number(item.get("start"), "Uniform load %d start" % index)
        end = _number(item.get("end"), "Uniform load %d end" % index)
        if magnitude < 0:
            raise ValueError("Uniform load magnitudes cannot be negative.")
        if not 0 <= start <= span or not 0 <= end <= span:
            raise ValueError("Uniform load positions must be within the beam span.")
        uniform_loads.append(UniformLoad(magnitude, start, end))

    return BeamModel(
        preset="Custom",
        support=support,
        span=span,
        material=material,
        section=section,
        deflection_limit=deflection_limit,
        point_loads=point_loads,
        uniform_loads=uniform_loads,
    )


def save_beam_file(path, model):
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(model_to_data(model), handle, indent=2)
        handle.write("\n")


def open_beam_file(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError("The selected file is not valid JSON.") from exc
    return data_to_model(data)
