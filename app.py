from flask import Flask, request, jsonify, redirect, url_for, render_template, session
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image 
from tensorflow.keras.models import load_model 
from PIL import Image
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import string
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = 'rerfg8fd4v5gtdfvxfvhdvcx7fvcx45gyb'  

OTP_LENGTH = 6
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'brainiac.team.web@gmail.com'
SMTP_PASSWORD = 'iyar esnl kztv ehnc' 
SENDER_EMAIL = 'brainiac.team.web@gmail.com'

model = load_model('braintumor_best_91_acc.h5')
labels = ['Glioma_Tumor', 'Meningioma_Tumor', 'No_Tumor', 'Pituitary_Tumor']

otp_storage = {}

client = MongoClient('mongodb://localhost:27017/')
db = client['brainiac']
comments_collection = db['comments']
locations_collection = db['locations']

# Helper functions
def preprocess_image(img):
    img = img.resize((150, 150))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = img_array / 255.0  
    return img_array

def generate_otp():
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))

def send_otp_email(email, first_name, last_name, otp):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg['Subject'] = 'Your OTP Verification Code from Brainiac'

    body = f"""
    <html>
      <body>
        <p>Dear {first_name} {last_name},</p>
        <p>Thank you for using Brainiac!</p>
        <p>To complete your login process, please use the following One-Time Password (OTP) for verification:</p>
        <p>Your OTP Code: <h2><strong>{otp}</strong></h2></p>
        <p>Please enter this code on the Brainiac login page to verify your email address.</p>
        <p>If you did not initiate this request, please ignore this email.</p>
        <p>Thank you for choosing Brainiac!</p>
        <p>Best regards,<br>The Brainiac Team</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, email, msg.as_string())

# Routes
@app.route('/')
def index():
    return render_template('final.html')

@app.route('/start')
def start():
    return render_template('login.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    otp = generate_otp()
    otp_storage[email] = {'otp': otp, 'first_name': first_name, 'last_name': last_name}
    send_otp_email(email, first_name, last_name, otp)
    return jsonify({'success': True})

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    stored_data = otp_storage.get(email)

    if stored_data and stored_data['otp'] == otp:
        del otp_storage[email]
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return redirect(url_for('index', error='No file provided'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index', error='No file selected'))

    try:
        img = Image.open(file.stream)
        img_array = preprocess_image(img)
        predictions = model.predict(img_array)
        predicted_class = np.argmax(predictions[0])
        prediction_label = labels[predicted_class]

        city = session.get('city')
        session['prediction'] = prediction_label
        return redirect(url_for('result'))
    except Exception as e:
        print(f"Error processing the file: {e}")
        return redirect(url_for('upload', error='Error processing the file'))

@app.route('/result')
def result():
    if 'prediction' not in session:
        return render_template('notloggedin.html'), 403
    prediction = session['prediction']
    city = session.get('city')
    

    print(prediction , city)
    
    return render_template('my_result.html', prediction=prediction, city=city)

@app.route('/upload')
def upload():
    if session.get('prediction'):
        session.pop('prediction', None)
    if not session.get('logged_in'):
        return render_template('notloggedin.html'), 401
    return render_template('my_upload.html')


@app.route('/submit_login', methods=['POST'])
def submit_login():
    data = request.get_json()
    city = data.get('city')
    fullname= data.get('first_name')+" "+data.get('last_name')
    email = data.get('email')

    if not city:
        return jsonify({'success': False, 'error': 'No location selected'})
    
    session['city'] = city
    session['logged_in'] = True
    session['user_email'] = data.get('email', email)  # fallback if not provided
    session['user_name'] = data.get('name', fullname)

    print(f"✅ Session stored: {dict(session)}")  

    return jsonify({'redirect_url': url_for('upload')})


@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    data = request.form
    name = data.get('name')
    email_comment = data.get('email_comment')
    comment = data.get('comment')

    if name and email_comment and comment:
        comments_collection.insert_one({
            'name': name,
            'email_comment': email_comment,
            'comment': comment,
            'reply': '',
            'status':''
        })
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'All fields are required'})
    
@app.route('/delete_comment/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    result = comments_collection.delete_one({'_id': ObjectId(comment_id)})
    
    if result.deleted_count > 0:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})

def send_reply_to_email(comment):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = comment['email_comment']
    msg['Subject'] = 'Reply to Your Comment'

    body = f"""
    <html>
      <body>
        <p>Dear {comment['name']},</p>
        <p>Thank you for your comment!</p>
        <p>Here is our response:</p>
        <div style="border:solid 1px rgb(66, 66, 66); border-radius:3px; background-color:grey; padding:5px;">
        <strong>{comment['reply']}</strong>
        </div>
        <p>If you have any further questions, feel free to reach out.</p>
        <p>Best regards,<br>The Brainiac Team</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, comment['email_comment'], msg.as_string())

@app.route('/send_reply', methods=['POST'])
def send_reply():
    comment_id = request.form.get('comment_id')
    reply = request.form.get('reply')

    print(f"Received comment_id: {comment_id}")
    print(f"Received reply: {reply}")

    if comment_id and reply:
        try:
            comment_id = ObjectId(comment_id)
            result = comments_collection.update_one(
                {'_id': comment_id},
                {'$set': {'reply': reply, 'status': 'sent'}}
            )
            comment = comments_collection.find_one({'_id': comment_id})
            if comment:
                send_reply_to_email(comment)
                    
                return jsonify({"success": True}), 200

        except Exception as e:
            print(f"Error: {e}")
    
    return jsonify({"success": False}), 500

@app.route('/admin', methods=['GET'])
def admin():
    # Fetch location data
    locations = locations_collection.find()

    # Fetch comments
    pending_comments = comments_collection.find({"status": ""})
    sent_comments = comments_collection.find({"status": "sent"})

    return render_template('newadmin.html',
                           pending_comments=pending_comments,
                           sent_comments=sent_comments,
                           locations=locations)


@app.route('/manage_locations', methods=['POST'])
def manage_locations():
    data = request.get_json()

    if 'location_id' in data:
        location_id = ObjectId(data['location_id'])
        location_name = data.get('location_name')
        hospitals = data.get('hospitals', [])

        update_data = {}
        if location_name:
            update_data['location_name'] = location_name
        if hospitals:
            update_data['hospitals'] = hospitals

        if update_data:
            locations_collection.update_one({'_id': location_id}, {'$set': update_data})
            return jsonify({'success': True})

    elif 'location_name' in data:
        location_name = data['location_name']
        hospitals = data.get('hospitals', [])
        locations_collection.insert_one({'location_name': location_name, 'hospitals': hospitals})
        return jsonify({'success': True})

    elif 'location_id_delete' in data:
        location_id_delete = ObjectId(data['location_id_delete'])
        locations_collection.delete_one({'_id': location_id_delete})
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid request'})


@app.route('/delete_location', methods=['POST'])
def delete_location():
    location_id = request.form.get('location_id')

    if location_id:
        try:
            location_id = ObjectId(location_id)
            result = locations_collection.delete_one({'_id': ObjectId(location_id)})
            if result.deleted_count > 0:
                return jsonify({'success': True}), 200
        except Exception as e:
            print(f"Error: {e}")

    return jsonify({'success': False}), 500

@app.route('/update_hospitals/<inpcity>', methods=['POST'])
def update_hospitals(inpcity):
    try:
        # Retrieve and parse form data
        form_data = request.json

        # Debugging: Print the received JSON payload
        print("Received form data:", form_data)

        # Extracting values from the form data
        inpcity = form_data.get('inpcity', inpcity)  # Use inpcity from URL if not in JSON
        hospital_names = form_data.get('hospital_name[]', [])
        contact_numbers = form_data.get('contact_number[]', [])

        # Ensure hospital_names and contact_numbers are lists
        if isinstance(hospital_names, str):
            hospital_names = [hospital_names]
        if isinstance(contact_numbers, str):
            contact_numbers = [contact_numbers]

        # Ensure both lists are of the same length
        if len(hospital_names) != len(contact_numbers):
            return jsonify({'success': False, 'error': 'Mismatched hospital names and contact numbers'}), 400

        # Create list of hospital dictionaries
        hospitals = [{"name": hospital_names[i], "phone": contact_numbers[i]} for i in range(len(hospital_names))]

        # Debugging: Print the list of hospitals to be updated or added
        print("Hospitals to update or add:", hospitals)

        # Check if the location exists
        existing_location = locations_collection.find_one({'city': inpcity})

        if existing_location:
            # Update the existing location with the new hospital data
            result = locations_collection.update_one(
                {'city': inpcity},
                {'$set': {'hospitals': hospitals}}
            )

            # Debugging: Print result of the update operation
            print(f"Updated {result.modified_count} document(s).")

            if result.modified_count > 0:
                return jsonify({'success': True, 'message': 'Location updated successfully.'})
            else:
                return jsonify({'success': False, 'error': 'No changes made'}), 304
        else:
            # Add a new location with the provided hospital data
            new_location = {
                'city': inpcity,
                'hospitals': hospitals
            }

            result = locations_collection.insert_one(new_location)

            # Debugging: Print the result of the insert operation
            print(f"Inserted document with ID: {result.inserted_id}")

            if result.inserted_id:
                return jsonify({'success': True, 'message': 'New location added successfully.'})
            else:
                return jsonify({'success': False, 'error': 'Failed to add new location'}), 500
    except Exception as e:
        # Log the error message for debugging
        print(f"Error updating or adding hospitals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_cities')
def get_cities():
    # Fetch all documents from the collection
    cities = locations_collection.find({}, { 'city': 1})
    
    # Convert to list of dictionaries
    city_list = [{"_id": str(city['_id']), "value": city['city'], "text": city['city']} for city in cities]
    
    return jsonify({"cities": city_list})

@app.route('/get_hospitals/<city>', methods=['GET'])
def get_hospitals(city):
    # Fetch the document for the specified city
    city_data = locations_collection.find_one({"city": city}, {'_id': 0, 'hospitals': 1})
    
    if city_data:
        return jsonify({"hospitals": city_data['hospitals']})
    else:
        return jsonify({"error": "City not found"}), 404
    
@app.route('/edit_hospitals/<location_id>', methods=['GET'])
def edit_hospitals(location_id):
    try:
        # Find the location in the database using the provided location_id
        location = locations_collection.find_one({'_id': ObjectId(location_id)})
        
        # If location is found, return hospitals data
        if location:
            hospitals = location.get('hospitals', [])
            return jsonify({'location_name': location.get('city'), 'hospitals': hospitals})
        else:
            return jsonify({'error': 'Location not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    




if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True)





