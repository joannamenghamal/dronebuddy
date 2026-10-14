import cv2
from djitellopy import Tello

from app.person_detector import load_model, detect_objects
from app.person_tracker import get_direction, get_distance_status
from app.control.follow_controller import get_drone_action


# Load YOLO model
model = load_model("yolo11n.pt")

# Connect to Tello
tello = Tello()

try:
    print("Connecting to Tello...")
    tello.connect()

    print(f"Battery: {tello.get_battery()}%")

    # Start Tello camera
    print("Starting video stream...")
    tello.streamon()

    frame_read = tello.get_frame_read()

    print("Camera stream started.")
    print("Point the camera at yourself.")
    print("Press Q to quit.")

    while True:
        frame = frame_read.frame

        if frame is None:
            continue

        # Run YOLO detection
        objects = detect_objects(model, frame)

        # Draw detected objects
        for label, (x1, y1, x2, y2) in objects:

            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                label.upper(),
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # Only use the tracker for people
            if label == "person":

                box = (x1, y1, x2, y2)

                direction = get_direction(
                    box,
                    frame.shape[1]
                )

                distance = get_distance_status(box)
                action = get_drone_action(direction, distance)

                print(
                    f"Person: {direction} | {distance} | Action: {action}"
                )

                # Display tracking information
                cv2.putText(
                    frame,
                    f"Action: {action}",
                    (20, 110),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )
               
                cv2.putText(
                    frame,
                    f"Direction: {direction}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Distance: {distance}",
                    (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

        cv2.imshow("Tello - Person Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    print("Stopping Tello...")

    tello.streamoff()
    tello.end()

    cv2.destroyAllWindows()

    print("Disconnected from Tello.")