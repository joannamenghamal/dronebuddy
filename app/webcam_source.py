import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("dronebuddy.video")


class WebcamSource:
    """Laptop camera feed for --drone mock."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._capture: Optional[cv2.VideoCapture] = None

    def start(self) -> None:
        self._capture = cv2.VideoCapture(self.camera_index)
        if not self._capture.isOpened():
            self._capture = None
            raise RuntimeError(
                f"Could not open camera {self.camera_index}. Check that:\n"
                "  - your terminal / code editor is allowed to use the camera\n"
                "      macOS:   System Settings > Privacy & Security > Camera\n"
                "      Windows: Settings > Privacy > Camera\n"
                "  - no other app (Zoom, FaceTime, Teams) is using the camera\n"
                "  - if you have more than one camera, try CAMERA_INDEX=1"
            )
        logger.info("webcam %s opened", self.camera_index)

    def read(self) -> Optional[np.ndarray]:
        if self._capture is None:
            return None
        ok, frame = self._capture.read()
        return frame if ok else None

    def stop(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
