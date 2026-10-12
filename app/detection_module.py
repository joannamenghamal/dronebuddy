from dataclasses import dataclass

from ultralytics import YOLO

PERSON_LABEL = "person"

## ByteTrack keeps the same ID on a person across frames, even through brief occlusion
TRACKER_CONFIG = "bytetrack.yaml"

## Detections below this confidence are dropped. Measured on our DJI clips: real people
## scored 0.53-0.94, tree trunks mistaken for people never scored above 0.43
MIN_CONFIDENCE = 0.5


@dataclass
class Detection:
    label: str
    box: tuple             # (x1, y1, x2, y2) in pixels
    track_id: int = None   # Persistent ID from ByteTrack, None if not tracked yet
    confidence: float = 1.0


def load_model(weights_path):
    return YOLO(weights_path)


def detect_objects(model, frame, min_confidence=MIN_CONFIDENCE):
    """Runs YOLO + ByteTrack on a frame and returns a Detection for every object.
    Not filtered to any one class - callers decide which labels matter to them.

    persist=True keeps tracker state between calls, so call this once per frame
    in order on the same video stream."""
    results = model.track(frame, persist=True, tracker=TRACKER_CONFIG, verbose=False)

    boxes = results[0].boxes  # Extract detected boxes

    detections = []

    ## Loop through the detected boxes
    for box in boxes:
        confidence = float(box.conf[0])
        if confidence < min_confidence:
            continue

        class_id = int(box.cls[0])
        label = model.names[class_id]

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        ## The tracker only assigns IDs once it's confident an object is real
        track_id = int(box.id[0]) if box.id is not None else None

        detections.append(Detection(label, (x1, y1, x2, y2), track_id, confidence))

    return detections
