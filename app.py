from flask import Flask, request, jsonify, render_template
import os
from ultralytics import YOLO
import cv2
import mysql.connector # NEW: Import the database driver

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
RESULTS_FOLDER = 'static/results'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

print("🔄 Loading CivicSense Pro AI Brain into memory...")
model = YOLO('best.pt')

# NEW: Function to connect to the database securely
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # Change this if your MySQL username is different
        password=os.getenv("DB_PASSWORD", "YOUR_MYSQL_PASSWORD_HERE"),  # Replace with your actual MySQL password
        database="civicsense_db"
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    
    # 1. Save Raw Image
    raw_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(raw_path)
    
    # 2. AI Inference
    results = model.predict(source=raw_path, save=False, conf=0.5, iou=0.4)
    
    # 3. Extract Confidence Score (NEW)
    # We grab the confidence of the first detected box (if any exist)
    confidence = 0.0
    if len(results[0].boxes) > 0:
        confidence = float(results[0].boxes[0].conf[0]) * 100
        
    # 4. Save Analyzed Image
    annotated_frame = results[0].plot()
    result_filename = "analyzed_" + file.filename
    result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
    cv2.imwrite(result_path, annotated_frame)
    
    web_image_path = '/' + result_path.replace('\\', '/')
    
    # 5. NEW: Insert the data into MySQL
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        sql_query = """
            INSERT INTO reports (raw_image_name, analyzed_image_path, latitude, longitude, confidence_score)
            VALUES (%s, %s, %s, %s, %s)
        """
        data_tuple = (file.filename, web_image_path, lat, lng, confidence)
        
        cursor.execute(sql_query, data_tuple)
        db.commit() # Save the changes permanently
        print("💾 Record successfully written to MySQL database!")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        # Always close the connection to prevent memory leaks
        if 'cursor' in locals(): cursor.close()
        if 'db' in locals(): db.close()

    return jsonify({
        'message': 'Hazard Detected & Recorded in Database!',
        'result_img_url': web_image_path, 
        'lat': lat,
        'lng': lng
    })

# ==========================================
# ROUTE 3: The Admin Dashboard (Retrieving the data)
# ==========================================
@app.route('/admin')
def admin_dashboard():
    try:
        # 1. Connect to the database
        db = get_db_connection()
        # dictionary=True makes the data much easier to read in HTML
        cursor = db.cursor(dictionary=True) 
        
        # 2. Fetch all reports, sorting the newest ones to the top
        cursor.execute("SELECT * FROM reports ORDER BY report_time DESC")
        all_reports = cursor.fetchall()
        
    except Exception as e:
        print(f"❌ Admin retrieval error: {e}")
        all_reports = []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'db' in locals(): db.close()

    # 3. Send the data to a new HTML page called admin.html
    return render_template('admin.html', reports=all_reports)

# ==========================================
# ROUTE 4: The Map API (Sending GPS data to the map)
# ==========================================
@app.route('/api/map-data')
def get_map_data():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        # We only need the coordinates, ID, and confidence for the map markers
        cursor.execute("SELECT id, latitude, longitude, confidence_score, analyzed_image_path FROM reports WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        map_points = cursor.fetchall()
        
        # Convert Decimals to standard floats so the web browser can read them
        for point in map_points:
            point['latitude'] = float(point['latitude'])
            point['longitude'] = float(point['longitude'])
            point['confidence_score'] = float(point['confidence_score'])
            
        return jsonify(map_points)
    except Exception as e:
        print(f"❌ Map API error: {e}")
        return jsonify([])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'db' in locals(): db.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)