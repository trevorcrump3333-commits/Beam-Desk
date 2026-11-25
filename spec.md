# Beam Designer

## Purpose

A Python desktop application for engineers and students to analyze steel and
lumber beams. The app presents beam inputs, a graphical beam drawing, shear,
moment, and deflection diagrams, and bending and deflection pass/fail checks.

## Platform

- Use Python 3 with Tkinter and Tkinter Canvas.
- Use the Python standard library where practical.
- Use NumPy or another lightweight numerical dependency only if needed.
- The application must run as a native desktop window on Windows, macOS, and
  Linux.
- Do not use HTML, CSS, JavaScript, or a browser-based UI.
- Do not depend on a web server or network connection.

## Users

A civil engineering student checking a homework beam, or an engineer sizing a
floor beam or deck joist.

## Layout

- Include a native File menu with Save and Open commands.
- Save stores the current beam settings: support type, span, material and
  section, deflection limit, and all point and uniform loads. Open restores
  those settings and loads into the application.
- Use a top header containing the application title and a Print / Save PDF
  Report action.
- Place beam inputs in a left-hand controls panel.
- Place the beam drawing, diagrams, and check cards in a resizable right-hand
  analysis panel.
- Stack the controls above the analysis area on small desktop windows.
- Use a light background, white panels, soft borders or subtle shadows, one
  accent color, and a modern system font.
- Keep controls grouped and uncluttered.

## Inputs

- Load preset: a selector in the beam settings panel with four presets:
  - Default: 20 ft Steel Floor Beam
  - 12 ft Wood Deck Joist
  - 10 ft Steel Cantilever Canopy
  - 30 ft Heavy Girder
- Support type: simply supported or cantilever fixed at the left end.
- Span: 4 to 40 ft, represented by a synchronized slider and number entry.
- Point loads:
  - Magnitude in kips, with downward positive.
  - Position in feet.
  - A new point load starts at midspan, or at the free end for a cantilever.
- Uniform loads:
  - Magnitude in kips/ft.
  - Start and end positions in feet.
- Buttons to add and remove point and uniform loads.
- Point loads may be dragged in the Canvas drawing and snap to 0.25 ft.
- Loads extending beyond the beam end are clipped to the beam length.
- Material and section selection:

  Steel W-shapes (E = 29,000 ksi, allowable bending stress Fb = 30 ksi):

  | Section | Ix (in^4) | Sx (in^3) | Weight (lb/ft) |
  |---------|-----------|-----------|----------------|
  | W8x10   | 30.8      | 7.81      | 10 |
  | W10x12  | 53.8      | 10.9      | 12 |
  | W12x26  | 204       | 33.4      | 26 |
  | W14x22  | 199       | 29.0      | 22 |
  | W16x26  | 301       | 38.4      | 26 |
  | W18x35  | 510       | 57.6      | 35 |
  | W21x44  | 843       | 81.6      | 44 |
  | W24x55  | 1350      | 114       | 55 |

  Douglas Fir-Larch No. 2 lumber (E = 1,600 ksi, Fb = 0.900 ksi):

  | Section | Ix (in^4) | Sx (in^3) |
  |---------|-----------|-----------|
  | 2x8     | 47.63     | 13.14     |
  | 2x10    | 98.93     | 21.39     |
  | 2x12    | 177.98    | 31.64     |

- Deflection limit: L/240 or L/360, defaulting to L/360.
- Self-weight is ignored.
- Invalid values must be blocked or clearly reported before recalculation.

## Calculations

- Reactions from statics.
- Shear and moment along the beam at 1 ft spacing or finer, including exactly
  every point-load position and uniform-load start/end.
- Deflection y(x) by integrating M/EI twice with the appropriate boundary
  conditions:
  - Simply supported: y = 0 at both supports.
  - Cantilever: y = 0 and slope = 0 at the fixed end.
- Bending stress: fb = |M max| x 12 / Sx (ksi).
- The bending check passes when fb <= Fb.
- Deflection passes when |y max| <= L/240 or L/360, with L in inches.
- Lightest passing section:
  - Steel: the lightest section that passes both checks; if equal in weight,
    select the section with the larger Ix.
  - Lumber: the first lumber size in table order that passes.
- Units: kips, ft, and kip-ft in the interface; inches for deflection.
- Sign convention:
  - Downward loads positive.
  - Upward reactions positive.
  - Positive shear pushes the left side up.
  - Positive bending moment causes compression on top.
  - Downward deflection positive.

## Outputs

- Tkinter Canvas drawing with beam, supports, load arrows, and reactions.
- Point loads use single arrows; uniform loads use a row of small arrows.
- Three diagrams stacked under the beam and aligned to the same horizontal
  scale: shear, moment, and deflected shape.
- Filled diagram regions with maximum values labeled at their locations.
- A mouse crosshair across the Canvas diagrams shows V, M, and y at the
  selected beam position.
- Two check cards for bending and deflection. Each shows actual value,
  allowable value, a ratio bar, and PASS or FAIL.
- Ratio bar colors: green below 70%, amber from 70% through 100%, and red
  above 100%.
- A label naming the lightest passing section and a "Use suggested section"
  button.
- An Export CSV button opens a save-file dialog and writes one row per
  analysis location, with columns x (ft), shear V (kips), moment M (kip-ft),
  and deflection y (in).
- Print / Save PDF Report action opens a print-friendly report window or
  invokes the operating system print dialog. The report includes inputs,
  reactions, maximum shear, maximum moment, maximum deflection, and status.
- Recalculate immediately whenever an input changes.
- Show formula help when hovering or focusing each check card.

## Startup State

- Open with the 20 ft simply supported W12x26 example and a 1 kip/ft uniform
  load over the full span.
- The example must present meaningful diagrams and passing check cards at
  startup.

## Validation

1. Simply supported, 20 ft, W12x26, uniform 1 kip/ft over full span:
   reactions 10 k and 10 k; max shear 10 k; max moment 50.0 kip-ft at
   10 ft; fb = 17.96 ksi; max deflection 0.609 in at 10 ft; L/360 =
   0.667 in; both checks pass.
2. Simply supported, 20 ft, W12x26, point load 10 k at 5 ft:
   reactions 7.5 k left and 2.5 k right; max moment 37.5 kip-ft at 5 ft;
   fb = 13.47 ksi; max deflection 0.340 in at 8.82 ft.
3. Cantilever, 10 ft, W12x26, point load 5 k at free end:
   reaction 5 k and fixed-end moment 50 kip-ft; max deflection 0.487 in at
   the free end; L/360 = 0.333 in, so deflection fails.
4. Simply supported, 12 ft, 2x10 joist, uniform 0.05 kip/ft:
   max moment 0.90 kip-ft; fb = 0.505 ksi; max deflection 0.147 in; both
   checks pass.

## Technical Structure

- Keep the implementation in maintainable Python modules.
- Separate beam input/state, calculations, section tables, and Tkinter UI.
- Reuse one state object or model for controls and drawing.
- Render and recalculate on the Tk event loop.
- Use Tkinter variables and bindings for synchronized controls.
- Redraw efficiently when inputs change.
- Support normal window resize and high-DPI display scaling.
- Package user-facing settings and section properties in data structures rather
  than hard-coded UI branches.

## Out of Scope

- Self-weight, shear stress, lateral-torsional buckling, load combinations,
  and continuous beams.

## Build Stages

1. Application shell
   - Build the Tkinter window, header, controls panel, and analysis panel.
   - Add no real calculations initially.
   - Verify desktop layout and window resizing.

2. Input model and controls
   - Add synchronized span slider and entry.
   - Add support, material, section, deflection limit, and load controls.
   - Implement add/remove load operations and preset loading.
   - Block invalid values or show clear validation messages.

3. Beam drawing and load rendering
   - Draw the beam and supports with Tkinter Canvas.
   - Render point and uniform loads.
   - Add point-load dragging with 0.25 ft snapping.
   - Clip loads outside the beam.

4. Reactions, shear, and moment
   - Implement reaction, shear, and moment calculations.
   - Apply the required 1 ft or finer sampling and exact load breakpoints.
   - Validate the numerical examples.

5. Deflection and checks
   - Add EI-based deflection integration.
   - Implement bending and deflection checks.
   - Implement lightest-passing-section selection.
   - Add check cards and suggested-section controls.

6. Diagram and report polish
   - Add hover crosshairs and values.
   - Add filled diagrams and maximum labels.
   - Add ratio bars and startup defaults.
   - Add print or PDF report support.
   - Verify the final desktop workflow end to end.
