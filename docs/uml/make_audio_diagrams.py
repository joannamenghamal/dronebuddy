"""Generates the audio part's UML and UI drawings as SVG:

    docs/uml/audio_class_diagram.svg          classes of the audio and voice part
    docs/uml/audio_sequence_where_is.svg      "where is my cup?" from push-to-talk to the answer
    docs/uml/audio_activity_push_to_talk.svg  push-to-talk, phone app and Python side
    docs/ui/push_to_talk_mockup.svg           the phone's full-screen push-to-talk screen

The names, methods and phrases mirror the code in app/. If you change the code,
update the tables here and rerun:
    python docs/uml/make_audio_diagrams.py
"""
import os
from html import escape

UML_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(os.path.dirname(UML_DIR), "ui")

FONT = "Segoe UI, Arial, sans-serif"
INK = "#1f2933"
MUTED = "#52606d"
HEADER_IN = "#e3ecd9"      # inputs from the rest of the pipeline
HEADER_AUDIO = "#fbe3cc"   # what the user hears
HEADER_VOICE = "#dde7f5"   # what the user asks
HEADER_DATA = "#eef0f3"    # data records
PLANNED = "#b44d12"


## ---------- SVG helpers ----------

def text(x, y, content, anchor="start", size=13, weight=None, style=None, fill=INK):
    attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if style:
        attrs += f' font-style="{style}"'
    return f'<text {attrs} xml:space="preserve">{escape(content)}</text>'


def line(points, dashed=False, head="open", tail=None, color=INK, width=1.4):
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dash = ' stroke-dasharray="7,5"' if dashed else ""
    markers = (f' marker-end="url(#{head})"' if head else "") + (f' marker-start="url(#{tail})"' if tail else "")
    return f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="{width}"{dash}{markers}/>'


def rect(x, y, w, h, fill="#fff", stroke=INK, rx=0, width=1.4, dashed=False):
    dash = ' stroke-dasharray="6,4"' if dashed else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{dash}/>'


DEFS = f"""<defs>
  <marker id="open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse">
    <path d="M1,1 L11,6 L1,11" fill="none" stroke="{INK}" stroke-width="1.4"/>
  </marker>
  <marker id="filled" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse">
    <path d="M1,1 L11,6 L1,11 Z" fill="{INK}"/>
  </marker>
  <marker id="diamond" viewBox="0 0 20 12" refX="19" refY="6" markerWidth="20" markerHeight="12" orient="auto-start-reverse">
    <path d="M1,6 L10,1 L19,6 L10,11 Z" fill="{INK}"/>
  </marker>
  <marker id="hollow" viewBox="0 0 16 16" refX="15" refY="8" markerWidth="16" markerHeight="16" orient="auto-start-reverse">
    <path d="M1,1 L15,8 L1,15 Z" fill="#fff" stroke="{INK}" stroke-width="1.4"/>
  </marker>
</defs>"""


def svg_document(width, height, parts):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
            f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="{FONT}">\n'
            f'<rect width="100%" height="100%" fill="#ffffff"/>\n{DEFS}\n' + "\n".join(parts) + "\n</svg>\n")


def save(directory, name, svg, width, height):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {path} ({width:.0f}x{height:.0f})")


## ---------- 1. Class diagram ----------

BOX_W = 250
LINE_H = 18
PAD = 8
CHAR_W = 7.1

## name -> (stereotype, title, header color, attributes, operations)
CLASSES = {
    "main": ("module", "main", "#d9f0e3", [], [
        "+ run(platform, source, muted, voice_script)",
        "Each frame: detect → select user → TrackingModule → ComputeActions → ObjectLocator → voice commands → follow → SafetyManager",
    ]),
    "tracking": (None, "TrackingModule", HEADER_IN, [
        "- tracks: dict[int, PersonTrack]",
    ], [
        "+ update(people, w, h): list[ActivityEvent]",
        "+ activity_of(track_id): str",
    ]),
    "actions": (None, "ComputeActions", HEADER_AUDIO, [
        "- cooldown_s = 5.0",
        "- message_cooldown_s = 2.0",
    ], [
        "+ compute(events): list[Alert]",
    ]),
    "locator": (None, "ObjectLocator", HEADER_AUDIO, [
        "- cooldown_s = 10.0",
        "- last_seen: label → (time, position, pan)",
    ], [
        "+ locate(detections, user, w, h): list[(label, position, message, pan)]",
        "+ find(label): str",
        "+ pan_of(label): float",
    ]),
    "audio": (None, "AudioOutput", HEADER_AUDIO, [
        "- backend: speech backend",
        "- pending: list[Utterance], at most 3",
        "- volume = 1.0",
        "- last_spoken: str",
    ], [
        "+ say(text, priority, pan, repeatable)",
        "+ repeat_last(): bool",
        "+ change_volume(step): float",
        "+ close()",
    ]),
    "voice": (None, "VoiceControl", HEADER_VOICE, [
        "- audio: AudioOutput",
        "- locator: ObjectLocator",
    ], [
        "+ handle(command): bool  (False = end session)",
    ]),
    "mic": (None, "FakeMic", HEADER_VOICE, [
        "- script: list[(seconds, VoiceCommand)]",
    ], [
        "+ start() / stop()",
        "+ poll(): list[VoiceCommand]",
        "Stands in for the phone mic (--voice-script)",
    ]),
    "logger": (None, "SessionLogger", HEADER_IN, [
        "+ path: str",
    ], [
        "+ log(event, **details)",
        "+ close(): str",
    ]),
    "event": ("dataclass", "ActivityEvent", HEADER_DATA, [
        "+ track_id: int",
        "+ activity: NEW | APPROACHING | MOVING AWAY | STANDING STILL | MOVING | LEFT FRAME",
        "+ horizontal_error: float",
        "+ height_ratio: float",
    ], []),
    "alert": ("dataclass", "Alert", HEADER_DATA, [
        "+ text: str",
        "+ priority: Priority",
        "+ pan: float  (-1 left .. +1 right)",
    ], []),
    "detection": ("dataclass", "Detection", HEADER_DATA, [
        "+ label: str",
        "+ box: (x1, y1, x2, y2)",
        "+ track_id: int",
        "+ confidence: float",
    ], []),
    "utterance": ("dataclass", "Utterance", HEADER_DATA, [
        "+ text: str",
        "+ priority: Priority",
        "+ pan: float",
        "+ volume: float",
        "+ repeatable: bool",
    ], []),
    "command": ("dataclass", "VoiceCommand", HEADER_DATA, [
        "+ type: CommandType",
        "+ argument: str  (WHERE_IS: \"cup\")",
        "+ heard_text: str",
        "+ confidence: float",
    ], []),
    "command_type": ("enum", "CommandType", HEADER_DATA, [
        "START_SESSION | STOP_SESSION | WHERE_IS | REPEAT | LOUDER | QUIETER",
    ], []),
    "bridge": ("module", "bridge_messages", HEADER_VOICE, [], [
        "+ say_message(text, priority, pan, volume): dict",
        "+ parse_voice_command(message): VoiceCommand",
        "Sent / received through DJIController",
    ]),
    "priority": ("enum", "Priority", HEADER_DATA, [
        "NORMAL | URGENT",
    ], []),
    "backend": ("protocol", "speech backend", HEADER_AUDIO, [], [
        "+ speak(utterance)",
    ]),
    "local": (None, "LocalSpeech", HEADER_DATA, [], [
        "laptop speakers (pyttsx3, offline)",
    ]),
    "silent": (None, "SilentSpeech", HEADER_DATA, [
        "+ spoken: list[Utterance]",
    ], [
        "--mute and tests",
    ]),
    "bridgespeech": (None, "BridgeSpeech", HEADER_DATA, [
        "- send(message)",
    ], [
        "phone speaks it (stereo, tones)",
    ]),
}


def wrap(content, width_px):
    max_chars = int(width_px / CHAR_W)
    lines, current = [], ""
    for word in content.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars or len(current.strip()) <= 1:
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

    @property
    def right(self):
        return self.x + self.w

    def svg(self):
        out = [rect(self.x, self.y, self.w, self.h), rect(self.x, self.y, self.w, self.header_h, fill=self.color)]
        ty = self.y + LINE_H
        if self.stereotype:
            out.append(text(self.cx, ty, f"«{self.stereotype}»", anchor="middle", size=11.5, style="italic"))
            ty += LINE_H
        out.append(text(self.cx, ty, self.title, anchor="middle", weight="bold"))
        y = self.y + self.header_h
        if self.attr_h:
            for i, l in enumerate(self.attr_lines):
                out.append(text(self.x + PAD, y + LINE_H * (i + 1), l))
            y += self.attr_h
            out.append(f'<line x1="{self.x}" y1="{y}" x2="{self.right}" y2="{y}" stroke="{INK}" stroke-width="1.2"/>')
        for i, l in enumerate(self.op_lines):
            is_note = not l.lstrip().startswith("+") and not l.startswith("    ")
            color = PLANNED if l.startswith("Proposed") else INK
            out.append(text(self.x + PAD, y + LINE_H * (i + 1), l, style="italic" if is_note else None, fill=color))
        return "\n".join(out)


def label(x, y, content, anchor="start"):
    return text(x, y, content, anchor=anchor, size=12, style="italic", fill="#3b4a5a")


def class_diagram():
    gap = 26
    cols = [20 + i * (BOX_W + gap) for i in range(7)]
    width = cols[-1] + BOX_W + 20

    main = Box("main", width / 2 - 300, 70, width=600)
    row1_y = main.bottom + 80
    row1 = [Box(k, cols[i], row1_y) for i, k in enumerate(["tracking", "actions", "locator", "audio", "voice", "mic", "logger"])]
    by = {b.key: b for b in row1}

    row2_y = max(b.bottom for b in row1) + 90
    event, alert, detection = Box("event", cols[0], row2_y), Box("alert", cols[1], row2_y), Box("detection", cols[2], row2_y)
    utterance, command = Box("utterance", cols[3], row2_y), Box("command", cols[4], row2_y)
    command_type, bridge = Box("command_type", cols[5], row2_y), Box("bridge", cols[6], row2_y)

    row3_y = max(b.bottom for b in [event, alert, detection, utterance, command, command_type, bridge]) + 80
    priority = Box("priority", cols[1], row3_y)
    backend = Box("backend", cols[3], row3_y)
    row4_y = backend.bottom + 80
    local, silent, bridgespeech = Box("local", cols[2], row4_y), Box("silent", cols[3], row4_y), Box("bridgespeech", cols[4], row4_y)

    boxes = [main] + row1 + [event, alert, detection, utterance, command, command_type, bridge, priority, backend, local, silent, bridgespeech]
    height = max(b.bottom for b in boxes) + 90
    parts = [text(20, 34, "Visual Buddy audio and voice: UML class diagram", size=22, weight="bold"),
             text(20, 56, "Generated from app/  ·  «module» = Python module of functions  ·  «dataclass» = data record  ·  «protocol» = any class with these methods", size=12.5, fill=MUTED)]

    ## main creates and calls each frame: one bus, drops on the right of each box
    bus_y = main.bottom + 40
    drop = lambda b: b.right - 36
    parts.append(line([(main.cx, main.bottom), (main.cx, bus_y)], head=None))
    parts.append(line([(drop(row1[0]), bus_y), (drop(row1[-1]), bus_y)], head=None))
    for b in row1:
        parts.append(line([(drop(b), bus_y), (drop(b), b.y)]))
    parts.append(label(main.cx + 10, main.bottom + 26, "creates and calls each frame"))

    t, a, loc, au, vo, mi = by["tracking"], by["actions"], by["locator"], by["audio"], by["voice"], by["mic"]
    ## data each component creates or reads
    parts.append(line([(t.cx - 40, t.bottom), (event.cx - 40, event.y)], dashed=True))
    parts.append(label(t.cx - 32, t.bottom + 36, "«create»"))
    parts.append(line([(a.cx - 40, a.bottom), (alert.cx - 40, alert.y)], dashed=True))
    parts.append(label(a.cx - 32, a.bottom + 36, "«create»"))
    parts.append(line([(a.x + 20, a.bottom), (a.x + 20, a.bottom + 50), (event.right - 30, a.bottom + 50), (event.right - 30, event.y)], dashed=True))
    parts.append(label(a.x + 28, a.bottom + 66, "«use»"))
    parts.append(line([(loc.cx - 40, loc.bottom), (detection.cx - 40, detection.y)], dashed=True))
    parts.append(label(loc.cx - 32, loc.bottom + 36, "«use»"))
    parts.append(line([(utterance.cx - 40, utterance.y), (au.cx - 40, au.bottom)], head="diamond"))
    parts.append(label(utterance.cx - 32, utterance.y - 10, "0..3 pending"))
    parts.append(line([(vo.cx - 40, vo.bottom), (command.cx - 40, command.y)], dashed=True))
    parts.append(label(vo.cx - 32, vo.bottom + 36, "«use»"))
    parts.append(line([(mi.cx - 40, mi.bottom), (mi.cx - 40, mi.bottom + 45), (command.right - 30, mi.bottom + 45), (command.right - 30, command.y)], dashed=True))
    parts.append(label(mi.cx - 32, mi.bottom + 36, "«create»"))
    parts.append(line([(command.right, command.y + 60), (command_type.x, command.y + 60)]))
    ## VoiceControl answers through AudioOutput and asks ObjectLocator (arrows between neighbours in row 1)
    parts.append(line([(vo.x, vo.y + 60), (au.right, vo.y + 60)]))
    parts.append(line([(vo.x, vo.y + 90), (vo.x - 13, vo.y + 90), (vo.x - 13, row1_y - 14), (loc.right - 70, row1_y - 14), (loc.right - 70, loc.y)]))
    parts.append(label(au.x + 8, row1_y - 20, "find(), pan_of()"))
    ## Priority is used by Alert and Utterance
    parts.append(line([(alert.cx, alert.bottom), (priority.cx, priority.y)]))
    mid_y = (max(b.bottom for b in [alert, detection, utterance]) + row3_y) / 2
    parts.append(line([(utterance.x + 30, utterance.bottom), (utterance.x + 30, mid_y), (priority.cx + 60, mid_y), (priority.cx + 60, priority.y)]))
    ## AudioOutput has one speech backend; three implement it
    parts.append(line([(au.right - 10, au.bottom), (au.right - 10, au.bottom + 20), (au.right + 13, au.bottom + 20),
                       (au.right + 13, backend.y + 30), (backend.right, backend.y + 30)]))
    parts.append(label(au.right + 18, backend.y + 22, "1 backend"))
    for impl in (local, silent, bridgespeech):
        parts.append(line([(impl.cx, impl.y), (impl.cx, impl.y - 40), (backend.cx, impl.y - 40), (backend.cx, backend.bottom)], dashed=True, head="hollow"))
    parts.append(line([(bridgespeech.right, bridgespeech.y + 40), (bridge.cx, bridgespeech.y + 40), (bridge.cx, bridge.bottom)], dashed=True))
    parts.append(label(bridgespeech.right + 8, bridgespeech.y + 32, "say_message()"))

    for b in boxes:
        parts.append(b.svg())

    ## legend
    lx, ly = cols[5], height - 40
    entries = [("calls / has", False, "open"), ("uses / creates", True, "open"), ("owns", False, "diamond"), ("implements", True, "hollow")]
    for i, (name, dashed, head) in enumerate(entries):
        x = lx + (i % 2) * 260
        y = ly + (i // 2) * 22 - 22
        parts.append(line([(x, y), (x + 46, y)], dashed=dashed, head=head))
        parts.append(text(x + 56, y + 4, name, size=12))

    svg = svg_document(width, height, parts)
    save(UML_DIR, "audio_class_diagram.svg", svg, width, height)


## ---------- 2. Sequence diagram: "where is my cup?" ----------

def sequence_diagram():
    lifelines = [("user", "User", None), ("phone", "Phone app", "push-to-talk + speech-to-text"),
                 ("main", "main loop", "+ MicInput"), ("voice", "VoiceControl", None),
                 ("locator", "ObjectLocator", None), ("audio", "AudioOutput", "+ BridgeSpeech")]
    spacing, left = 205, 110
    x = {key: left + i * spacing for i, (key, _, _) in enumerate(lifelines)}
    width = x["audio"] + 170
    top = 90
    parts = [text(20, 34, "“Where is my cup?”: UML sequence diagram", size=22, weight="bold"),
             text(20, 56, "From holding the phone's screen to the answer in the user's ear. Orange: the two bridge messages.", size=12.5, fill=MUTED)]

    messages = [
        # (kind, from, to, label, note)
        ("loop", "main", "locator", "locate(detections, user, w, h)", "every frame: remembers where each object was last seen"),
        ("call", "user", "phone", "holds the screen: “where is my mug?”", None),
        ("self", "phone", None, "vibrate, stop speech, recognize; “mug” → cup", None),
        ("bridge", "phone", "main", "voice_command {WHERE_IS, cup}", None),
        ("call", "main", "voice", "handle(command)", None),
        ("call", "voice", "locator", "find(\"cup\")", None),
        ("return", "locator", "voice", "“Cup on your left”, pan -0.7", None),
        ("call", "voice", "audio", "say(answer, URGENT, pan -0.7)", None),
        ("bridge", "audio", "phone", "say {“Cup on your left”, URGENT, pan -0.7}", None),
        ("return", "phone", "user", "speaks it, in the left ear", None),
    ]
    step = 58
    y0 = top + 80
    bottom = y0 + step * len(messages) + 30

    for key, name, sub in lifelines:
        cx = x[key]
        parts.append(rect(cx - 82, top, 164, 46 if sub else 36, fill=HEADER_VOICE if key in ("phone", "voice") else HEADER_AUDIO if key in ("audio", "locator") else HEADER_DATA, rx=6))
        parts.append(text(cx, top + 22, name, anchor="middle", weight="bold"))
        if sub:
            parts.append(text(cx, top + 38, sub, anchor="middle", size=11, fill=MUTED))
        parts.append(line([(cx, top + 46), (cx, bottom)], dashed=True, head=None, color="#9aa5b1", width=1.2))

    ## loop fragment around the first message
    fy = y0 - 26
    parts.append(rect(x["main"] - 40, fy, x["locator"] - x["main"] + 300, step - 4, fill="none", width=1.1))
    parts.append(rect(x["main"] - 40, fy, 52, 18, fill=HEADER_DATA, width=1.1))
    parts.append(text(x["main"] - 34, fy + 13, "loop", size=11.5, weight="bold"))

    for i, (kind, src, dst, words, note) in enumerate(messages):
        y = y0 + i * step
        if kind == "self":
            cx = x[src]
            parts.append(line([(cx, y - 8), (cx + 44, y - 8), (cx + 44, y + 12), (cx + 2, y + 12)], head="filled"))
            parts.append(text(cx + 52, y + 6, words, size=12.5))
            continue
        x1, x2 = x[src], x[dst]
        color = PLANNED if kind == "bridge" else INK
        dashed = kind == "return"
        head = "open" if dashed else "filled"
        parts.append(line([(x1, y), (x2 + (-4 if x2 > x1 else 4), y)], dashed=dashed, head=head, color=color))
        mid = (x1 + x2) / 2
        parts.append(text(mid, y - 8, words, anchor="middle", size=12.5, fill=color, weight="bold" if kind == "bridge" else None))
        if note:
            parts.append(text(x[dst] + 12, y + 18, note, size=11.5, style="italic", fill=MUTED))

    note_y = bottom + 20
    parts.append(rect(20, note_y, width - 40, 50, fill="#fff7ed", stroke=PLANNED, rx=6, dashed=True))
    parts.append(text(36, note_y + 21, "Python's side of both bridge messages is built. Until the phone app handles them, test with --drone mock:", size=12.5))
    parts.append(text(36, note_y + 39, "--voice-script stands in for the phone's voice_command, and the laptop speaks the answer.", size=12.5))
    height = note_y + 70
    svg = svg_document(width, height, parts)
    save(UML_DIR, "audio_sequence_where_is.svg", svg, width, height)


## ---------- 3. Activity diagram: push-to-talk ----------

def activity_diagram():
    lane_w = 420
    lanes = [("Phone app", 20, HEADER_VOICE), ("Python assistant", 20 + lane_w, HEADER_AUDIO)]
    width = 20 + 2 * lane_w + 20
    top = 80
    parts = [text(20, 34, "Push-to-talk: UML activity diagram", size=22, weight="bold"),
             text(20, 56, "The whole phone screen is one button; the answer always comes back out loud.", size=12.5, fill=MUTED)]

    pc, qc = 20 + lane_w / 2, 20 + lane_w * 1.5   # lane centers
    bw, bh = 300, 46

    def action(cx, cy, words, planned=False):
        out = [rect(cx - bw / 2, cy - bh / 2, bw, bh, fill="#fff", rx=18, stroke=PLANNED if planned else INK)]
        out.append(text(cx, cy + 5, words, anchor="middle", size=13))
        return "\n".join(out)

    def decision(cx, cy, words):
        d = 36
        pts = f"{cx},{cy - d} {cx + d * 1.6},{cy} {cx},{cy + d} {cx - d * 1.6},{cy}"
        return f'<polygon points="{pts}" fill="#fff" stroke="{INK}" stroke-width="1.4"/>' + text(cx, cy + 4, words, anchor="middle", size=11.5)

    ys = {}
    y = top + 70
    for key in ["start", "wait", "press", "listen", "release", "confident", "send", "handle", "stop", "answer", "speak", "end"]:
        ys[key] = y
        y += 74
    height = ys["end"] + 70

    for name, lx, color in lanes:
        parts.append(rect(lx, top, lane_w, height - top - 20, fill="none", width=1.2))
        parts.append(rect(lx, top, lane_w, 30, fill=color, width=1.2))
        parts.append(text(lx + lane_w / 2, top + 20, name, anchor="middle", weight="bold"))

    parts.append(f'<circle cx="{pc}" cy="{ys["start"]}" r="11" fill="{INK}"/>')
    parts.append(action(pc, ys["wait"], "Wait: the whole screen is the button"))
    parts.append(action(pc, ys["press"], "Pressed: vibrate, stop any speech"))
    parts.append(action(pc, ys["listen"], "Listen while the screen is held"))
    parts.append(action(pc, ys["release"], "Released: vibrate, speech-to-text"))
    parts.append(decision(pc, ys["confident"], "known command?"))
    parts.append(action(pc, ys["send"], "Send voice_command over the bridge", planned=True))
    parts.append(action(qc, ys["handle"], "VoiceControl.handle(command)"))
    parts.append(decision(qc, ys["stop"], "STOP_SESSION?"))
    parts.append(action(qc, ys["answer"], "Answer out loud: say(…, URGENT)"))
    parts.append(action(pc, ys["speak"], "Speak the answer (say message)", planned=True))
    parts.append(action(qc, ys["end"] - 30, "Say “Session ended”, end session"))
    parts.append(f'<circle cx="{qc}" cy="{ys["end"] + 18}" r="12" fill="#fff" stroke="{INK}" stroke-width="1.6"/>'
                 f'<circle cx="{qc}" cy="{ys["end"] + 18}" r="7" fill="{INK}"/>')

    down = lambda cx, a, b, ya=bh / 2, yb=bh / 2: line([(cx, ys[a] + ya), (cx, ys[b] - yb)])
    parts.append(line([(pc, ys["start"] + 11), (pc, ys["wait"] - bh / 2)]))
    parts.append(down(pc, "wait", "press"))
    parts.append(text(pc + 8, ys["wait"] + 44, "screen pressed", size=11.5, style="italic", fill=MUTED))
    parts.append(down(pc, "press", "listen"))
    parts.append(down(pc, "listen", "release"))
    parts.append(text(pc + 8, ys["listen"] + 44, "screen released", size=11.5, style="italic", fill=MUTED))
    parts.append(line([(pc, ys["release"] + bh / 2), (pc, ys["confident"] - 36)]))
    parts.append(line([(pc, ys["confident"] + 36), (pc, ys["send"] - bh / 2)]))
    parts.append(text(pc + 8, ys["confident"] + 52, "yes", size=11.5, style="italic", fill=MUTED))
    ## not understood -> back to waiting, quietly
    left_x = 20 + 18
    parts.append(line([(pc - 58, ys["confident"]), (left_x, ys["confident"]), (left_x, ys["wait"]), (pc - bw / 2, ys["wait"])]))
    parts.append(text(left_x + 6, ys["confident"] - 8, "no: drop it", size=11.5, style="italic", fill=MUTED))
    ## across to Python
    parts.append(line([(pc + bw / 2, ys["send"]), (qc, ys["send"]), (qc, ys["handle"] - bh / 2)], color=PLANNED))
    parts.append(line([(qc, ys["handle"] + bh / 2), (qc, ys["stop"] - 36)]))
    parts.append(line([(qc, ys["stop"] + 36), (qc, ys["answer"] - bh / 2)]))
    parts.append(text(qc + 8, ys["stop"] + 52, "no", size=11.5, style="italic", fill=MUTED))
    right_x = 20 + 2 * lane_w - 18
    parts.append(line([(qc + 58, ys["stop"]), (right_x, ys["stop"]), (right_x, ys["end"] - 30), (qc + bw / 2, ys["end"] - 30)]))
    parts.append(text(right_x - 6, ys["stop"] - 8, "yes", anchor="end", size=11.5, style="italic", fill=MUTED))
    parts.append(line([(qc, ys["end"] - 30 + bh / 2), (qc, ys["end"] + 6)]))
    ## answer back to the phone, then waiting again
    parts.append(line([(qc, ys["answer"] + bh / 2), (qc, ys["speak"]), (pc + bw / 2, ys["speak"])], color=PLANNED))
    loop_x = 20 + lane_w - 14
    parts.append(line([(pc, ys["speak"] - bh / 2), (pc, ys["speak"] - bh / 2 - 6), (loop_x, ys["speak"] - bh / 2 - 6),
                       (loop_x, ys["wait"] - 30), (pc + 40, ys["wait"] - 30), (pc + 40, ys["wait"] - bh / 2)]))
    parts.append(text(loop_x - 8, ys["speak"] - bh / 2 - 14, "back to waiting", anchor="end", size=11.5, style="italic", fill=MUTED))

    parts.append(text(20, height - 4, "Orange: the bridge messages. The phone app's side is not built yet; until then --voice-script and the laptop speaker stand in.", size=11.5, fill=PLANNED))
    svg = svg_document(width, height + 10, parts)
    save(UML_DIR, "audio_activity_push_to_talk.svg", svg, width, height + 10)


## ---------- 4. UI mockup: the phone's push-to-talk screen ----------

def mockup():
    pw, ph = 300, 600
    width, height = 1240, 760
    parts = [text(30, 40, "Phone push-to-talk screen: UI mockup", size=24, weight="bold"),
             text(30, 64, "Planned for the Android bridge app. Designed for a user who can't see the screen: the whole screen is one button.", size=13, fill=MUTED)]

    def phone(x, y, bg, fg, title, line1, line2, caption, rings):
        out = [rect(x, y, pw, ph, fill="#0d1117", stroke="#0d1117", rx=36),
               rect(x + 12, y + 14, pw - 24, ph - 28, fill=bg, stroke=bg, rx=26),
               text(x + pw / 2, y + 44, "Visual Buddy · connected", anchor="middle", size=12, fill=fg)]
        cx, cy = x + pw / 2, y + 250
        for i in range(rings):
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{70 + i * 22}" fill="none" stroke="{fg}" stroke-opacity="{0.45 - i * 0.12:.2f}" stroke-width="3"/>')
        out.append(f'<circle cx="{cx}" cy="{cy}" r="58" fill="{fg}" fill-opacity="0.16" stroke="{fg}" stroke-width="3"/>')
        ## microphone icon
        out.append(rect(cx - 13, cy - 30, 26, 42, fill=fg, stroke=fg, rx=13))
        out.append(f'<path d="M{cx - 24},{cy - 2} a24,24 0 0 0 48,0" fill="none" stroke="{fg}" stroke-width="4"/>')
        out.append(f'<line x1="{cx}" y1="{cy + 22}" x2="{cx}" y2="{cy + 34}" stroke="{fg}" stroke-width="4"/>')
        out.append(text(cx, y + 390, line1, anchor="middle", size=26, weight="bold", fill=fg))
        out.append(text(cx, y + 422, line2, anchor="middle", size=16, fill=fg))
        out.append(rect(x + 30, y + 500, pw - 60, 54, fill=fg, stroke=fg, rx=10))
        out[-1] = out[-1].replace('fill="' + fg + '"', f'fill="{fg}" fill-opacity="0.12"', 1)
        out.append(text(cx, y + 522, caption[0], anchor="middle", size=11.5, fill=fg))
        out.append(text(cx, y + 541, caption[1], anchor="middle", size=13, weight="bold", fill=fg))
        out.append(text(cx, y + ph + 32, title, anchor="middle", size=15, weight="bold"))
        return out

    parts += phone(60, 100, "#11161c", "#f2f4f7", "Waiting", "Hold anywhere", "to talk",
                   ("Last alert (for a helper)", "Person approaching, ahead"), 0)
    parts += phone(420, 100, "#f2a541", "#1b2430", "Held: listening", "Listening…", "release to send",
                   ("Heard", "where is my mug"), 3)

    notes = [
        ("Whole screen = one button", "no target to find; press anywhere, any orientation"),
        ("Felt, not seen", "short vibration on press and on release"),
        ("Pressing stops speech", "so the mic hears the user, not the last alert"),
        ("Works with TalkBack on", "the screen reader must not turn the press into “read this”"),
        ("Screen stays awake", "the phone is in a hand or pocket, not being looked at"),
        ("For a sighted helper", "large, high-contrast text: state, last alert, what was heard"),
        ("Answer is spoken", "“Cup on your left”, from the left ear in stereo"),
    ]
    nx, ny = 800, 120
    for i, (head, body) in enumerate(notes):
        y = ny + i * 82
        parts.append(f'<circle cx="{nx + 14}" cy="{y + 8}" r="14" fill="#f2a541"/>')
        parts.append(text(nx + 14, y + 13, str(i + 1), anchor="middle", size=13, weight="bold"))
        parts.append(text(nx + 40, y + 13, head, size=16, weight="bold"))
        parts.append(text(nx + 40, y + 36, body, size=13, fill=MUTED))

    svg = svg_document(width, height, parts)
    save(UI_DIR, "push_to_talk_mockup.svg", svg, width, height)


if __name__ == "__main__":
    class_diagram()
    sequence_diagram()
    activity_diagram()
    mockup()
