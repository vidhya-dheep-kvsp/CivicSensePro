import cv2
from ultralytics import YOLO

print("Loading the AI Brain into memory...")
# 1. Initialize the YOLO model using the pre-trained weights file
model= YOLO('best.pt')

print("Running image through neural network layers...")
# 2. Pass your image to the model to scan for features
results=model('test.jpg', conf=0.5, iou=0.4)

print("Rendering bounding boxes on screen...")
# 3. Pull the first array item and pop open a window showing what the AI saw
results[0].show()