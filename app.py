import requests
import json
import os
import time
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Set up logging to print to the terminal
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

API_KEY = '15adc73ab0314db9a39b13b5362af82f_55fac8e475874662b24b060a71fe9e33_andoraitools'
GENERATION_URL = 'https://api.lightxeditor.com/external/api/v1/caricature'
STATUS_URL = 'https://api.lightxeditor.com/external/api/v1/order-status'

# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    logging.info("Rendering index page")
    return render_template('index.html')

@app.route('/generate_caricature', methods=['POST'])
def generate_caricature():
    try:
        image_url = request.form.get('imageUrl')
        style_image_url = request.form.get('styleImageUrl')

        logging.info(f"Received request to generate caricature with imageUrl: {image_url}, styleImageUrl: {style_image_url}")

        if not image_url:
            logging.error("No image URL provided")
            return jsonify({'status': 'error', 'message': 'No image URL provided'}), 400

        payload = {
            "imageUrl": image_url,
            "textPrompt": "Generate caricature"
        }

        if style_image_url:
            payload['styleImageUrl'] = style_image_url

        headers = {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json'
        }

        logging.info(f"Sending POST request to {GENERATION_URL} with payload: {payload}")

        response = requests.post(GENERATION_URL, headers=headers, json=payload)

        logging.info(f"API Response Status Code: {response.status_code}")
        logging.debug(f"API Response Text: {response.text}")

        if response.status_code == 200:
            response_data = response.json()

            if response_data and 'body' in response_data and response_data['body'].get('orderId'):
                order_id = response_data['body'].get('orderId')
                logging.info(f"Received orderId: {order_id}, returning processing status.")
                return jsonify({'status': 'processing', 'orderId': order_id})
            else:
                logging.error("OrderId missing in API response")
                return jsonify({'status': 'error', 'message': 'orderId missing in API response'}), 500
        else:
            logging.error(f"Unexpected API Response: {response.text}")
            return jsonify({'status': 'error', 'message': f"Unexpected API Response: {response.text}"}), response.status_code

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/check_status/<order_id>', methods=['GET'])
def check_status(order_id):
    max_retries = 5
    print("inside check status")
    retry_interval = 6
    url = STATUS_URL

    payload = {
        "orderId": order_id
    }

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
    }

    retries = 0
    
    while retries < max_retries:
        try:
            logging.info(f"Sending POST request to check status for orderId: {order_id} (Retry {retries + 1}/{max_retries})")

            response = requests.post(url, headers=headers, json=payload)
            # print(response.status_code)
            # logging.info(f"API Response Status Code: {response.status_code}")
            # logging.debug(f"API Response Text: {response.text}")

            if response.status_code == 200:
                response_json = response.json()
                print(response_json)
                body_data=response_json.get('body')
                status = body_data.get('status')

                # logging.info(f"Status received: {status}")

                if status == 'active':
                    # logging.info(f"Order {order_id} is active. Returning output.")
                    return jsonify({'status': 'active', 'output': body_data.get('output')})
                elif status == 'failed':
                    # logging.error(f"Order {order_id} failed.")
                    return jsonify({'status': 'failed', 'message': 'Order processing failed.'}), 400

                # logging.info(f"Status is {status}. Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
                retries += 1
            else:
                logging.error(f"Failed to retrieve order status. Status code: {response.status_code}, Response: {response.text}")
                return jsonify({'status': 'error', 'message': f'Failed to retrieve order status. Status code: {response.status_code}'}), response.status_code

        except Exception as e:
            logging.error(f"Error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    logging.error(f"Max retries exceeded for orderId: {order_id}")
    return jsonify({'status': 'error', 'message': 'Max retries exceeded, unable to retrieve active status.'}), 408

@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        if 'imageFile' not in request.files:
            logging.error("No image file part found in request")
            return jsonify({'status': 'error', 'message': 'No image file part'}), 400

        image_file = request.files['imageFile']

        if image_file.filename == '':
            logging.error("No selected image file")
            return jsonify({'status': 'error', 'message': 'No selected image file'}), 400

        filename = secure_filename(image_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(file_path)

        image_url = f'{request.host_url}uploads/{filename}'
        logging.info(f"Image uploaded successfully: {image_url}")
        
        return jsonify({'status': 'success', 'imageUrl': image_url})

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    logging.info("Starting Flask server")
    app.run(debug=False,host='0.0.0.0')
