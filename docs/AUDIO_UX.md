# Audio UX: what the user hears and says

The visually impaired user never looks at a screen: everything they get from
Visual Buddy is spoken, and everything they ask is a voice command on the
phone's push-to-talk screen. This page lists every phrase, when it's said, and
the rules that keep speech short and current. Every phrase here is in the code
(`app/main.py`, `app/compute_actions.py`, `app/object_locator.py`,
`app/voice_control.py`).

Diagrams: [class](uml/audio_class_diagram.png) ·
[sequence: "where is my cup?"](uml/audio_sequence_where_is.png) ·
[activity: push-to-talk](uml/audio_activity_push_to_talk.png) ·
[phone screen mockup](ui/push_to_talk_mockup.png)

## What the user hears

`{side}` is where the thing is: **ahead**, **on your left** or **on your
right** (the frame split into thirds; the drone flies behind the user, so the
left of the frame is their left). In the user's path, objects are **ahead**,
**ahead on your left** or **ahead on your right**.

| When | Phrase | Priority | Repeat limit | Sound comes from |
| --- | --- | --- | --- | --- |
| Session starts | "Visual Buddy ready" | NORMAL | once | center |
| A person comes into view | "Person {side}" | NORMAL | 5 s per person; same words 2 s | their side |
| A person comes toward the user | "Person approaching, {side}" | **URGENT** | 5 s per person; same words 2 s | their side |
| A person leaves the view | "Person out of view" | NORMAL | 5 s per person; same words 2 s | their last side |
| An object is in the user's path | "{object} ahead" / "… ahead on your left / right" | NORMAL | 10 s per kind of object | its side |
| Emergency stop (space bar) | "Emergency stop" | **URGENT** | once | center |
| Session ends | "Session ended" | NORMAL | once | center |

People standing still or moving away are logged for the caregiver but not
spoken. A person must be in view for 0.5 s before they're reported at all, so
brief false detections are never spoken.

**The user's path** is their own width plus one body-width on each side,
ahead of them, and no farther than 0.40 of the way down the frame (the line
the drone holds the user's head on). With no user in view, it is the middle
third of the frame.

## What the user can say

The phone recognizes these while its screen is held (push-to-talk). Every
answer is **URGENT**: the user just asked, so it goes ahead of routine alerts.

| Command | Example | Answer |
| --- | --- | --- |
| `WHERE_IS` | "where is my cup?" | "Cup on your left" · "Cup ahead, seen 5 seconds ago" · "I don't see a cup" · no object named: "Which object?" |
| `REPEAT` | "say again" | the last alert or answer again (never "Louder" or "Quieter"); nothing yet: "Nothing to repeat yet" |
| `LOUDER` / `QUIETER` | "louder" | "Louder" / "Quieter", at the new volume (steps of 0.2, never below 0.2) |
| `START_SESSION` | "start" | "Visual Buddy ready" |
| `STOP_SESSION` | "stop" | the session ends: "Session ended" |

`WHERE_IS` answers for any object seen anywhere in view in the last 30 s, not
only in the path, and the answer comes from that object's side.

## Rules that keep speech useful

- **Newest first.** At most 3 alerts wait; if speech falls behind, the oldest
  NORMAL one is dropped. A stale warning is worse than none.
- **Urgent first.** URGENT alerts go ahead of every NORMAL one still waiting.
  On the phone, an URGENT alert will also cut off a NORMAL one already playing.
- **Never about themselves.** The user the drone follows is never announced.
- **Stereo.** Every alert carries a `pan` from -1 (left ear) to +1 (right ear),
  so the sound comes from where the person or object is (on the phone, with
  headphones).
- **Pressing the screen stops speech**, so the mic hears the user and not the
  last alert.
- **Everything is logged** for the caregiver: alerts, commands and answers
  (`logs/session_*.jsonl`: `person_alert`, `object_alert`, `voice_command`,
  `voice_answer`).

## Not built yet

The Python side is connected: on `--drone dji` alerts go to the phone as
`say` messages and commands come from it as `voice_command` messages (see
`DRONE_BRIDGE.md`). On the phone, speaking is written
(`android-bridge/.../audio/SpeechPlayer.kt`: text-to-speech, URGENT cuts in,
stereo from `pan`) but not yet run on a device. Still missing:

- The push-to-talk screen and speech recognition that send `voice_command`.
- Tones for repeated warnings.

Until then, test with `--drone mock`: the laptop speaks, in mono, and
`--voice-script` stands in for the user's commands.
