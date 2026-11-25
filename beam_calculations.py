from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple


STEEL_SECTIONS = [
    {"name": "W8x10", "Ix": 30.8, "Sx": 7.81, "weight": 10},
    {"name": "W10x12", "Ix": 53.8, "Sx": 10.9, "weight": 12},
    {"name": "W12x26", "Ix": 204.0, "Sx": 33.4, "weight": 26},
    {"name": "W14x22", "Ix": 199.0, "Sx": 29.0, "weight": 22},
    {"name": "W16x26", "Ix": 301.0, "Sx": 38.4, "weight": 26},
    {"name": "W18x35", "Ix": 510.0, "Sx": 57.6, "weight": 35},
    {"name": "W21x44", "Ix": 843.0, "Sx": 81.6, "weight": 44},
    {"name": "W24x55", "Ix": 1350.0, "Sx": 114.0, "weight": 55},
]

LUMBER_SECTIONS = [
    {"name": "2x8", "Ix": 47.63, "Sx": 13.14, "weight": 0},
    {"name": "2x10", "Ix": 98.93, "Sx": 21.39, "weight": 0},
    {"name": "2x12", "Ix": 177.98, "Sx": 31.64, "weight": 0},
]


@dataclass
class PointLoad:
    magnitude: float
    position: float


@dataclass
class UniformLoad:
    magnitude: float
    start: float
    end: float


@dataclass
class BeamModel:
    preset: str = "Default: 20 ft Steel Floor Beam"
    support: str = "simply-supported"
    span: float = 20.0
    material: str = "Steel"
    section: str = "W12x26"
    deflection_limit: str = "L/360"
    point_loads: Sequence[PointLoad] = None
    uniform_loads: Sequence[UniformLoad] = None

    def __post_init__(self):
        if self.point_loads is None:
            self.point_loads = []
        if self.uniform_loads is None:
            self.uniform_loads = []


@dataclass
class Analysis:
    xs: List[float]
    shear: List[float]
    moment: List[float]
    deflection: List[float]
    reactions: Tuple[float, float]
    max_shear: float
    max_shear_x: float
    max_moment: float
    max_moment_x: float
    max_deflection: float
    max_deflection_x: float
    bending_stress: float
    bending_allowable: float
    bending_pass: bool
    deflection_allowable: float
    deflection_pass: bool
    suggested_section: str


def sections_for(material: str):
    return STEEL_SECTIONS if material == "Steel" else LUMBER_SECTIONS


def section_properties(material: str, name: str):
    for section in sections_for(material):
        if section["name"] == name:
            return section
    return sections_for(material)[0]


def sample_positions(span: float, point_loads: Iterable[PointLoad],
                     uniform_loads: Iterable[UniformLoad]) -> List[float]:
    positions = {0.0, span}
    step = 0.25
    x = 0.0
    while x <= span + 1e-9:
        positions.add(round(x, 4))
        x += step
    for load in point_loads:
        positions.add(round(min(max(load.position, 0.0), span), 4))
    for load in uniform_loads:
        positions.add(round(min(max(load.start, 0.0), span), 4))
        positions.add(round(min(max(load.end, 0.0), span), 4))
    return sorted(positions)


def positive_part(value: float) -> float:
    return value if value > 0 else 0.0


def shear_at(model: BeamModel, x: float, reactions: Tuple[float, float]) -> float:
    if model.support == "cantilever":
        shear = 0.0
        for load in model.point_loads:
            if load.position >= x - 1e-9:
                shear -= load.magnitude
        for load in model.uniform_loads:
            start = min(max(load.start, 0.0), model.span)
            end = min(max(load.end, 0.0), model.span)
            if end >= x:
                shear -= load.magnitude * (end - max(start, x))
        return shear

    shear = reactions[0]
    for load in model.point_loads:
        shear -= load.magnitude * (1 if x >= load.position - 1e-9 else 0)
    for load in model.uniform_loads:
        start = min(max(load.start, 0.0), model.span)
        end = min(max(load.end, 0.0), model.span)
        overlap = max(0.0, min(x, end) - start)
        shear -= load.magnitude * overlap
    return shear


def moment_at(model: BeamModel, x: float, reactions: Tuple[float, float]) -> float:
    if model.support == "cantilever":
        moment = 0.0
        for load in model.point_loads:
            if load.position > x:
                moment += load.magnitude * (load.position - x)
        for load in model.uniform_loads:
            start = min(max(load.start, 0.0), model.span)
            end = min(max(load.end, 0.0), model.span)
            clipped_start = max(start, x)
            if end > clipped_start:
                length = end - clipped_start
                moment += load.magnitude * length * (clipped_start + length / 2.0 - x)
        return moment

    moment = reactions[0] * x
    for load in model.point_loads:
        moment -= load.magnitude * positive_part(x - load.position)
    for load in model.uniform_loads:
        start = min(max(load.start, 0.0), model.span)
        end = min(max(load.end, 0.0), model.span)
        a = positive_part(x - start)
        b = positive_part(x - end)
        moment -= 0.5 * load.magnitude * (a * a - b * b)
    return moment


def reactions(model: BeamModel) -> Tuple[float, float]:
    point_total = sum(load.magnitude for load in model.point_loads)
    uniform_total = sum(
        load.magnitude * max(0.0, min(load.end, model.span) - min(max(load.start, 0.0), model.span))
        for load in model.uniform_loads
    )
    total = point_total + uniform_total

    if model.support == "cantilever":
        fixed_moment = sum(
            load.magnitude * load.position for load in model.point_loads
        ) + sum(
            load.magnitude
            * max(0.0, min(load.end, model.span) - min(max(load.start, 0.0), model.span))
            * ((min(max(load.start, 0.0), model.span) + min(max(load.end, 0.0), model.span)) / 2.0)
            for load in model.uniform_loads
        )
        return (-total, fixed_moment)

    point_moment = sum(load.magnitude * load.position for load in model.point_loads)
    uniform_moment = sum(
        load.magnitude
        * max(0.0, min(load.end, model.span) - min(max(load.start, 0.0), model.span))
        * ((min(max(load.start, 0.0), model.span) + min(max(load.end, 0.0), model.span)) / 2.0)
        for load in model.uniform_loads
    )
    rb = (point_moment + uniform_moment) / model.span
    ra = total - rb
    return (ra, rb)


def integrate_deflection(model: BeamModel, xs: Sequence[float],
                         moments: Sequence[float], E: float, Ix: float) -> List[float]:
    EI = E * Ix
    theta = 0.0
    y = 0.0
    raw_y = [0.0]
    theta_values = [0.0]

    for i in range(1, len(xs)):
        dx_ft = xs[i] - xs[i - 1]
        dx = dx_ft * 12.0
        m1 = moments[i - 1]
        m2 = moments[i]
        # M kip-ft converted to kip-in, then integrated in inches.
        curvature1 = m1 * 12.0 / EI
        curvature2 = m2 * 12.0 / EI
        theta += 0.5 * (curvature1 + curvature2) * dx
        y += 0.5 * (theta_values[-1] + theta) * dx
        theta_values.append(theta)
        raw_y.append(y)

    if model.support == "cantilever":
        return raw_y

    if xs[-1] > 0:
        span = xs[-1]
        return [raw - raw_y[-1] * x / span for raw, x in zip(raw_y, xs)]
    return raw_y


def suggested_section(model: BeamModel) -> str:
    for candidate in sections_for(model.material):
        analysis = calculate(model, override_section=candidate["name"], include_suggestion=False)
        if analysis.bending_pass and analysis.deflection_pass:
            if model.material == "Steel":
                return candidate["name"]
            return candidate["name"]

    candidates = sections_for(model.material)
    return candidates[-1]["name"]


def calculate(model: BeamModel, override_section: Optional[str] = None,
              include_suggestion: bool = True) -> Analysis:
    span = max(4.0, min(40.0, model.span))
    model_span = BeamModel(
        preset=model.preset,
        support=model.support,
        span=span,
        material=model.material,
        section=model.section,
        deflection_limit=model.deflection_limit,
        point_loads=model.point_loads,
        uniform_loads=model.uniform_loads,
    )
    xs = sample_positions(span, model.point_loads, model.uniform_loads)
    reacts = reactions(model_span)
    shear = [shear_at(model_span, x, reacts) for x in xs]
    moment = [moment_at(model_span, x, reacts) for x in xs]

    section_name = override_section or model.section
    section = section_properties(model.material, section_name)
    E = 29000.0 if model.material == "Steel" else 1600.0
    Ix = section["Ix"]
    Sx = section["Sx"]
    Fb = 30.0 if model.material == "Steel" else 0.900

    deflection = integrate_deflection(model_span, xs, moment, E, Ix)

    max_shear = max((abs(value), value, x) for value, x in zip(shear, xs))[0]
    max_shear_signed = max((abs(value), value, x) for value, x in zip(shear, xs))[1]
    max_shear_x = max((abs(value), x) for value, x in zip(shear, xs))[1]

    max_moment_record = max((abs(value), value, x) for value, x in zip(moment, xs))
    max_moment = abs(max_moment_record[1])
    max_moment_x = max_moment_record[2]

    max_deflection_record = max((abs(value), value, x) for value, x in zip(deflection, xs))
    max_deflection = abs(max_deflection_record[1])
    max_deflection_x = max_deflection_record[2]

    bending_stress = max_moment * 12.0 / Sx
    bending_pass = bending_stress <= Fb + 1e-9
    divisor = 360 if model.deflection_limit == "L/360" else 240
    deflection_allowable = span * 12.0 / divisor
    deflection_pass = max_deflection <= deflection_allowable + 1e-9

    # Candidate ranking is the steel weight/Ix rule; lumber uses table order.
    candidates = sections_for(model.material)
    suggested = candidates[-1]["name"]
    passing = []
    if include_suggestion:
        for candidate in candidates:
            candidate_model = BeamModel(
                preset=model.preset,
                support=model.support,
                span=span,
                material=model.material,
                section=candidate["name"],
                deflection_limit=model.deflection_limit,
                point_loads=model.point_loads,
                uniform_loads=model.uniform_loads,
            )
            candidate_analysis = calculate(candidate_model, include_suggestion=False)
            if candidate_analysis.bending_pass and candidate_analysis.deflection_pass:
                passing.append(candidate)
    if passing:
        if model.material == "Steel":
            passing.sort(key=lambda item: (item["weight"], -item["Ix"]))
        suggested = passing[0]["name"]

    return Analysis(
        xs=xs,
        shear=shear,
        moment=moment,
        deflection=deflection,
        reactions=reacts,
        max_shear=max_shear,
        max_shear_x=max_shear_x,
        max_moment=max_moment,
        max_moment_x=max_moment_x,
        max_deflection=max_deflection,
        max_deflection_x=max_deflection_x,
        bending_stress=bending_stress,
        bending_allowable=Fb,
        bending_pass=bending_pass,
        deflection_allowable=deflection_allowable,
        deflection_pass=deflection_pass,
        suggested_section=suggested,
    )
