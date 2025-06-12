import cv2
import numpy as np
import argparse
import datetime
import logging
import imutils
import time
import json
import csv
from imutils.video import VideoStream, FPS
from itertools import zip_longest
import math
import norfair
from norfair import Detection, Tracker

# Set up logging
logging.basicConfig(level=logging.INFO, format="[INFO] %(message)s")
logger = logging.getLogger(__name__)

# Load configuration (for CSV path and stream URL, and optional default FPS)
with open("utils/config.json", "r") as f:
    config = json.load(f)

def parse_arguments():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--prototxt", required=False,
                    help="(unused) kept for backward compatibility")
    ap.add_argument("-m", "--model", required=True,
                    help="path to Caffe pre-trained model (.caffemodel)")
    ap.add_argument("-i", "--input", type=str,
                    help="path to optional input video file")
    ap.add_argument("-o", "--output", type=str,
                    help="path to optional output video file")
    ap.add_argument("-c", "--confidence", type=float, default=0.4,
                    help="minimum probability to filter weak detections")
    ap.add_argument("--rect-x", type=int, default=None,
                    help="x-coordinate of top-left corner of counting rectangle")
    ap.add_argument("--rect-y", type=int, default=None,
                    help="y-coordinate of top-left corner of counting rectangle")
    ap.add_argument("--rect-w", type=int, default=None,
                    help="width of counting rectangle")
    ap.add_argument("--rect-h", type=int, default=None,
                    help="height of counting rectangle")
    ap.add_argument("--tilt-angle", type=float, default=0,
                    help="Camera tilt angle in degrees (positive = top tilts away from viewer)")
    return vars(ap.parse_args())

def log_data(move_in, in_time, move_out, out_time, stay_duration):
    """Log counting data (including precomputed stay durations) to CSV."""
    data = [move_in, in_time, move_out, out_time, stay_duration]
    export_data = zip_longest(*data, fillvalue="")
    with open("utils/data/logs/counting_data.csv", "w", newline="") as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        if myfile.tell() == 0:
            wr.writerow(("Move In", "In Time", "Move Out", "Out Time", "Stay Duration"))
        for row in export_data:
            wr.writerow(row)

def keystone_polygon(x, y, w, h, tilt_deg, frame_width):
    tilt_rad = math.radians(tilt_deg)
    max_shift = w // 3
    shift = int(max_shift * math.sin(abs(tilt_rad)))
    if tilt_deg > 0:
        pts = np.array([
            [x + shift, y],
            [x + w - shift, y],
            [x + w, y + h],
            [x, y + h]
        ])
    else:
        pts = np.array([
            [x, y],
            [x + w, y],
            [x + w - shift, y + h],
            [x + shift, y + h]
        ])
    pts[:, 0] = np.clip(pts[:, 0], 0, frame_width - 1)
    return pts

def point_in_polygon(point, polygon):
    x, y = point
    poly = polygon.tolist() if isinstance(polygon, np.ndarray) else polygon
    inside = False
    px1, py1 = poly[0]
    for i in range(len(poly) + 1):
        px2, py2 = poly[i % len(poly)]
        if y > min(py1, py2):
            if y <= max(py1, py2):
                if x <= max(px1, px2):
                    if py1 != py2:
                        xinters = (y - py1) * (px2 - px1) / (py2 - py1 + 1e-8) + px1
                    if px1 == px2 or x <= xinters:
                        inside = not inside
        px1, py1 = px2, py2
    return inside

def people_counter():
    args = parse_arguments()
    net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

    # Start video source
    if not args.get("input", False):
        vs = VideoStream(config["url"]).start()
        time.sleep(2.0)
        feed_fps = config.get("feed_fps", 30)
    else:
        vs = cv2.VideoCapture(args["input"])
        feed_fps = vs.get(cv2.CAP_PROP_FPS) or config.get("feed_fps", 30)

    writer = None
    W = H = None

    tracker = Tracker(distance_function="euclidean", distance_threshold=30)

    class RegionTrackable:
        def __init__(self, track_id, inside=False, entry_frame=None, entry_timestamp=None):
            self.track_id = track_id
            self.inside = inside
            self.entry_frame = entry_frame
            self.entry_timestamp = entry_timestamp

    trackableObjects = {}
    totalFrames = 0
    totalIn = 0
    totalOut = 0
    move_in = []
    move_out = []
    in_time = []
    out_time = []
    stay_duration = []
    fps = FPS().start()

    rect_x = args["rect_x"]
    rect_y = args["rect_y"]
    rect_w = args["rect_w"]
    rect_h = args["rect_h"]
    tilt_angle = args["tilt_angle"]
    polygon = None

    while True:
        frame = vs.read()
        frame = frame[1] if args.get("input", False) else frame
        if args.get("input", False) and frame is None:
            break

        frame = imutils.resize(frame, width=500)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if W is None or H is None:
            H, W = frame.shape[:2]
            if None in (rect_x, rect_y, rect_w, rect_h):
                rect_w = W
                rect_h = H // 4
                rect_x = 0
                rect_y = (H // 2) - (rect_h // 2)
            polygon = keystone_polygon(rect_x, rect_y, rect_w, rect_h, tilt_angle, W)

        if polygon is not None:
            cv2.polylines(frame, [polygon], isClosed=True, color=(0, 0, 255), thickness=2)

        if args.get("output") and writer is None:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(args["output"], fourcc, feed_fps, (W, H), True)

        # Detection
        blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
        net.setInput(blob)
        detections = net.forward()

        norfair_detections = []
        for i in np.arange(0, detections.shape[2]):
            conf = float(detections[0, 0, i, 2])
            if conf < args["confidence"]:
                continue
            cls = int(detections[0, 0, i, 1])
            if cls != 15: continue
            box = (detections[0, 0, i, 3:7] * [W, H, W, H]).astype(int)
            sx, sy, ex, ey = box
            cx, cy = (sx + ex)//2, (sy + ey)//2
            norfair_detections.append(
                Detection(points=np.array([[cx, cy]]), scores=np.array([conf]))
            )

        tracked_objects = tracker.update(detections=norfair_detections)

        for obj in tracked_objects:
            tid = obj.id
            cx, cy = obj.estimate.astype(int)[0]
            inside = point_in_polygon((cx, cy), polygon)
            to = trackableObjects.get(tid)

            if to is None:
                # First sighting
                if inside:
                    entry_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    to = RegionTrackable(tid, inside, entry_frame=totalFrames, entry_timestamp=entry_ts)
                    totalIn += 1
                    move_in.append(totalIn)
                    in_time.append(entry_ts)
                else:
                    to = RegionTrackable(tid, inside)
            else:
                if not to.inside and inside:
                    # Entering
                    entry_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    to.entry_frame = totalFrames
                    to.entry_timestamp = entry_ts
                    totalIn += 1
                    move_in.append(totalIn)
                    in_time.append(entry_ts)
                elif to.inside and not inside and to.entry_frame is not None:
                    # Exiting
                    exit_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    totalOut += 1
                    move_out.append(totalOut)
                    out_time.append(exit_ts)
                    dur = (totalFrames - to.entry_frame) / feed_fps
                    stay_duration.append(round(dur, 2))
                    to.entry_frame = None
                    to.entry_timestamp = None

                to.inside = inside

            trackableObjects[tid] = to

            cv2.putText(frame, f"ID {tid}", (cx-10, cy-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
            cv2.circle(frame, (cx, cy), 4, (255,255,255), -1)

        cv2.putText(frame, f"In: {totalIn}", (10, H-40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        cv2.putText(frame, f"Out: {totalOut}", (10, H-20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        # Log data
        log_data(move_in, in_time, move_out, out_time, stay_duration)

        if writer:
            writer.write(frame)
        cv2.imshow("People Counter", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        totalFrames += 1
        fps.update()

    fps.stop()
    logger.info(f"Elapsed time: {fps.elapsed():.2f} seconds")
    logger.info(f"Approx. FPS: {fps.fps():.2f}")

    if args.get("input"):
        vs.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    people_counter()
