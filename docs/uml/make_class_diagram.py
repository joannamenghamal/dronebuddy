"""Generates the Visual Buddy UML class diagram (class_diagram.svg) from the layout below.

The classes, fields and methods mirror the code in app/. If you change the code, update
the CLASSES table here and rerun:
    python docs/uml/make_class_diagram.py
"""
import os
from html import escape

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

FONT = "Segoe UI, Arial, sans-serif"
FONT_SIZE = 13
LINE_H = 18
CHAR_W = 6.7          # Rough average character width at FONT_SIZE, used for wrapping
BOX_W = 262
PAD = 8

INK = "#1f2933"
HEADER_A = "#dde7f5"  # Assistant pipeline
HEADER_B = "#fbe3cc"  # Drone follow extension
HEADER_DATA = "#eef0f3"

## name -> (stereotype, title, header color, attributes, operations)
CLASSES = {
    "main": ("module", "main  (app entry point)", "#d9f0e3", [], [
        "+ run(source)",
        "+ compute_follow_command(user, w, h): VelocityCommand",
        "+ draw_overlay(frame, detections, user, ...)",
        "Each frame: detect → select user → track others → alerts → follow → safety → draw",
    ]),
    "detection": ("module", "DetectionModule", HEADER_A, [
        "MIN_CONFIDENCE = 0.5",
        'TRACKER_CONFIG = "bytetrack.yaml"',
    ], [
        "+ load_model(weights_path): YOLO",
        "+ detect_objects(model, frame): list[Detection]",
    ]),
    "tracking": (None, "TrackingModule", HEADER_A, [
        "- tracks: dict[int, PersonTrack]",
        "- clock",
    ], [
        "+ update(people: list[Detection], w, h): list[ActivityEvent]",
        "+ activity_of(track_id): str",
    ]),
    "actions": (None, "ComputeActions", HEADER_A, [
        "- cooldown_s = 5.0",
        "- message_cooldown_s = 2.0",
        "- last_alert: dict",
        "- last_message: dict",
    ], [
        "+ compute(events: list[ActivityEvent]): list[str]",
    ]),
    "locator": (None, "ObjectLocator", HEADER_A, [
        "- cooldown_s = 10.0",
        "- last_announced: dict[str, float]",
    ], [
        "+ locate(detections: list[Detection], w, h): list[(label, position, message)]",
    ]),
    "audio": (None, "AudioOutput", HEADER_A, [
        "- pending: Queue[str]",
        "- thread: Thread",
        "- rate = 180",
    ], [
        "+ say(text)",
        "+ close()",
    ]),
    "logger": (None, "SessionLogger", HEADER_A, [
        "+ path: str",
        "- file",
        "- event_count: int",
    ], [
        "+ log(event, **details)",
        "+ close(): str",
    ]),
    "follow": ("module", "FollowController", HEADER_B, [
        "YAW_GAIN = 40.0",
        "FORWARD_GAIN = 2.0",
    ], [
        "+ get_drone_action(horizontal_error, head_ratio, head_cut_off): VelocityCommand",
    ]),
    "safety": (None, "SafetyManager", HEADER_B, [
        "- max_speed = 1.0 m/s",
        "- max_yaw = 30 °/s",
        "- land_after_lost_s = 5.0",
        "- emergency_stopped: bool",
    ], [
        "+ filter(command, target_seen): VelocityCommand",
        "+ should_land(): bool",
        "+ trigger_emergency_stop()",
        "+ reset_emergency_stop()",
        "+ status(): str",
    ]),
    "detection_dc": ("dataclass", "Detection", HEADER_DATA, [
        "+ label: str",
        "+ box: (x1, y1, x2, y2)",
        "+ track_id: int",
        "+ confidence: float",
    ], []),
    "person_track": (None, "PersonTrack", HEADER_DATA, [
        "+ track_id: int",
        "+ first_seen: float",
        "+ confirmed: bool",
        "+ activity: str",
        "- history: deque",
    ], [
        "+ add_sample(now, horizontal_error, height_ratio)",
        "+ classify(): str",
        "+ update_activity(): str",
    ]),
    "event": ("dataclass", "ActivityEvent", HEADER_DATA, [
        "+ track_id: int",
        "+ activity: NEW | APPROACHING | MOVING AWAY | STANDING STILL | MOVING | LEFT FRAME",
        "+ horizontal_error: float",
        "+ height_ratio: float",
    ], []),
    "geometry": ("module", "PersonTracker  (frame geometry, used by most classes)", HEADER_DATA, [
        "TARGET_HEAD_RATIO = 0.40",
        "HEAD_TOLERANCE = 0.08",
        "DEAD_ZONE = 0.10",
    ], [
        "+ select_user(people, locked_id, w, h): Detection",
        "+ get_horizontal_error(box, w): float",
        "+ get_head_ratio(box, h): float",
        "+ get_height_ratio(box, h): float",
        "+ is_head_cut_off(box, h): bool",
        "+ describe_position(horizontal_error): str",
        "+ get_distance_status(head_ratio): str",
    ]),
    "velocity": ("dataclass", "VelocityCommand", HEADER_DATA, [
        "+ forward: float  (m/s)",
        "+ right: float  (m/s)",
        "+ up: float  (m/s)",
        "+ yaw: float  (°/s)",
    ], [
        "+ is_hover(): bool",
    ]),
}

## Layout: x position of each column and which class sits where
GAP = 20
COLS_A = [20 + i * (BOX_W + GAP) for i in range(6)]
COLS_B = [COLS_A[-1] + BOX_W + 70 + i * (BOX_W + GAP) for i in range(2)]
WIDTH = COLS_B[-1] + BOX_W + 28

ROW1 = ["detection", "tracking", "actions", "locator", "audio", "logger"]
ROW1_B = ["follow", "safety"]


def wrap(text, width_px):
    """Splits text into lines that fit width_px, indenting continuation lines."""
    max_chars = int(width_px / CHAR_W)
    lines, current = [], ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = "    " + word
    lines.append(current)
    return lines


class Box:
    def __init__(self, key, x, y, width=BOX_W):
        stereotype, title, color, attrs, ops = CLASSES[key]
        self.key, self.x, self.y, self.w = key, x, y, width
        self.stereotype, self.title, self.color = stereotype, title, color
        inner = width - 2 * PAD
        self.attr_lines = [l for a in attrs for l in wrap(a, inner)]
        self.op_lines = [l for o in ops for l in wrap(o, inner)]
        self.header_h = (2 if stereotype else 1) * LINE_H + 10
        self.attr_h = max(len(self.attr_lines), 1) * LINE_H + 8 if (self.attr_lines or self.op_lines) else 0
        self.op_h = len(self.op_lines) * LINE_H + 8 if self.op_lines else 0
        self.h = self.header_h + self.attr_h + self.op_h

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def bottom(self):
        return self.y + self.h

    def svg(self):
        out = [f'<g class="box" id="{self.key}">']
        out.append(f'<rect x="{self.x}" y="{self.y}" width="{self.w}" height="{self.h}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
        out.append(f'<rect x="{self.x}" y="{self.y}" width="{self.w}" height="{self.header_h}" fill="{self.color}" stroke="{INK}" stroke-width="1.4"/>')
        ty = self.y + LINE_H
        if self.stereotype:
            out.append(text(self.cx, ty, f"«{self.stereotype}»", anchor="middle", size=11.5, style="italic"))
            ty += LINE_H
        out.append(text(self.cx, ty, self.title, anchor="middle", weight="bold"))

        y = self.y + self.header_h
        if self.attr_h:
            for i, line in enumerate(self.attr_lines):
                out.append(text(self.x + PAD, y + 4 + LINE_H * (i + 1) - 4, line))
            y += self.attr_h
            out.append(f'<line x1="{self.x}" y1="{y}" x2="{self.x + self.w}" y2="{y}" stroke="{INK}" stroke-width="1.2"/>')
        for i, line in enumerate(self.op_lines):
            italic = "italic" if line.startswith("Each frame") or line.strip().startswith("→") else None
            out.append(text(self.x + PAD, y + 4 + LINE_H * (i + 1) - 4, line, style=italic))
        out.append("</g>")
        return "\n".join(out)


def text(x, y, content, anchor="start", size=FONT_SIZE, weight=None, style=None, fill=INK):
    attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if style:
        attrs += f' font-style="{style}"'
    return f'<text {attrs} xml:space="preserve">{escape(content)}</text>'


def line(points, dashed=False, head="open", tail=None):
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dash = ' stroke-dasharray="7,5"' if dashed else ""
    markers = ""
    if head:
        markers += f' marker-end="url(#{head})"'
    if tail:
        markers += f' marker-start="url(#{tail})"'
    return f'<polyline points="{path}" fill="none" stroke="{INK}" stroke-width="1.4"{dash}{markers}/>'


def label(x, y, content, anchor="start"):
    return text(x, y, content, anchor=anchor, size=12, style="italic", fill="#3b4a5a")


def build():
    parts = []

    ## Main app at the top, centered over the assistant package
    main = Box("main", (COLS_A[0] + COLS_B[-1] + BOX_W) / 2 - 230, 70, width=460)

    package_top = main.bottom + 90
    row1_y = package_top + 40

    row1 = [Box(k, COLS_A[i], row1_y) for i, k in enumerate(ROW1)]
    row1_b = [Box(k, COLS_B[i], row1_y) for i, k in enumerate(ROW1_B)]
    by_key = {b.key: b for b in row1 + row1_b}

    row2_y = max(b.bottom for b in row1 + row1_b) + 110
    detection_dc = Box("detection_dc", COLS_A[0], row2_y)
    person_track = Box("person_track", COLS_A[1], row2_y)
    event = Box("event", COLS_A[2], row2_y)
    geometry = Box("geometry", COLS_A[3] + 40, row2_y, width=2 * BOX_W + GAP)
    velocity = Box("velocity", COLS_B[0], row2_y)

    boxes = [main] + row1 + row1_b + [detection_dc, person_track, event, geometry, velocity]
    bottom = max(b.bottom for b in boxes)
    height = bottom + 120

    ## Packages
    def package(x1, x2, title, color):
        return (
            f'<rect x="{x1}" y="{package_top - 26}" width="{len(title) * 7.6 + 24}" height="26" fill="{color}" stroke="{INK}" stroke-width="1.2"/>'
            + text(x1 + 12, package_top - 8, title, weight="bold")
            + f'<rect x="{x1}" y="{package_top}" width="{x2 - x1}" height="{bottom + 30 - package_top}" fill="none" stroke="{INK}" stroke-width="1.2"/>'
        )

    parts.append(package(COLS_A[0] - 12, COLS_A[-1] + BOX_W + 12, "Assistant pipeline (audio)", HEADER_A))
    parts.append(package(COLS_B[0] - 12, COLS_B[-1] + BOX_W + 12, "Drone follow (DJI Mini 3)", HEADER_B))

    ## main creates and calls every component each frame: one bus line with drops
    bus_y = main.bottom + 45
    targets = row1 + row1_b
    parts.append(line([(main.cx, main.bottom), (main.cx, bus_y)], head=None))
    ## Drops land on the right part of each box so they don't cross the package name tabs
    drop_x = lambda b: b.x + b.w - 40
    parts.append(line([(drop_x(targets[0]), bus_y), (drop_x(targets[-1]), bus_y)], head=None))
    for b in targets:
        parts.append(line([(drop_x(b), bus_y), (drop_x(b), b.y)]))
    parts.append(label(main.cx + 10, main.bottom + 28, "creates and calls each frame"))

    ## DetectionModule creates Detections
    parts.append(line([(by_key["detection"].cx, by_key["detection"].bottom), (detection_dc.cx, detection_dc.y)], dashed=True))
    parts.append(label(by_key["detection"].cx + 8, by_key["detection"].bottom + 40, "«create»"))

    ## TrackingModule owns PersonTracks
    tracking = by_key["tracking"]
    parts.append(line([(person_track.cx, person_track.y), (tracking.cx, tracking.bottom)], head="diamond"))
    parts.append(label(person_track.cx + 8, person_track.y - 10, "0..*"))
    parts.append(label(tracking.cx + 8, tracking.bottom + 22, "1"))

    ## TrackingModule creates ActivityEvents, ComputeActions consumes them
    actions = by_key["actions"]
    parts.append(line([(tracking.x + tracking.w - 30, tracking.bottom), (tracking.x + tracking.w - 30, tracking.bottom + 55), (event.x + 40, tracking.bottom + 55), (event.x + 40, event.y)], dashed=True))
    parts.append(label(tracking.x + tracking.w - 22, tracking.bottom + 48, "«create»"))
    parts.append(line([(actions.cx + 40, actions.bottom), (actions.cx + 40, event.y)], dashed=True))
    parts.append(label(actions.cx + 48, actions.bottom + 85, "«use»"))

    ## ObjectLocator uses the geometry helpers, ComputeActions / AudioOutput link
    locator = by_key["locator"]
    parts.append(line([(locator.cx + 40, locator.bottom), (locator.cx + 40, geometry.y)], dashed=True))
    parts.append(label(locator.cx + 48, locator.bottom + 40, "«use»"))

    ## FollowController creates VelocityCommands, SafetyManager filters them
    follow, safety = by_key["follow"], by_key["safety"]
    parts.append(line([(follow.cx, follow.bottom), (velocity.cx, velocity.y)], dashed=True))
    parts.append(label(follow.cx + 8, follow.bottom + 40, "«create»"))
    parts.append(line([(safety.cx, safety.bottom), (safety.cx, velocity.y + 40), (velocity.x + velocity.w, velocity.y + 40)], dashed=True))
    parts.append(label(safety.cx + 8, safety.bottom + 40, "«filter»"))

    for b in boxes:
        parts.append(b.svg())

    ## Title and legend
    parts.append(text(20, 34, "Visual Buddy — UML Class Diagram", size=22, weight="bold"))
    parts.append(text(20, 56, "Generated from the code in app/  ·  «module» = Python module of functions  ·  «dataclass» = plain data record", size=12.5, fill="#52606d"))

    legend_x, legend_y = COLS_B[0] - 12, bottom + 50
    parts.append(line([(legend_x, legend_y), (legend_x + 50, legend_y)]))
    parts.append(text(legend_x + 60, legend_y + 4, "association (calls)", size=12))
    parts.append(line([(legend_x + 200, legend_y), (legend_x + 250, legend_y)], dashed=True))
    parts.append(text(legend_x + 260, legend_y + 4, "dependency", size=12))
    parts.append(line([(legend_x + 360, legend_y), (legend_x + 410, legend_y)], head="diamond"))
    parts.append(text(legend_x + 420, legend_y + 4, "composition", size=12))

    defs = f"""<defs>
  <marker id="open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse">
    <path d="M1,1 L11,6 L1,11" fill="none" stroke="{INK}" stroke-width="1.4"/>
  </marker>
  <marker id="diamond" viewBox="0 0 20 12" refX="19" refY="6" markerWidth="20" markerHeight="12" orient="auto-start-reverse">
    <path d="M1,6 L10,1 L19,6 L10,11 Z" fill="{INK}"/>
  </marker>
</defs>"""

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH:.0f}" height="{height:.0f}" viewBox="0 0 {WIDTH:.0f} {height:.0f}" font-family="{FONT}">\n'
        f'<rect width="100%" height="100%" fill="#ffffff"/>\n{defs}\n' + "\n".join(parts) + "\n</svg>\n"
    )

    path = os.path.join(OUT_DIR, "class_diagram.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {path} ({WIDTH:.0f}x{height:.0f})")


if __name__ == "__main__":
    build()
