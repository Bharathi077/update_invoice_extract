from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from invoice_processor import process_file
import pandas as pd
import json
from datetime import datetime
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def create_temp_filename(original_filename):
    """Create a unique temporary filename."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"temp_{timestamp}_{secure_filename(original_filename)}"


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        # Create temporary file
        temp_filename = create_temp_filename(file.filename)
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)

        # Save uploaded file
        file.save(temp_filepath)

        # Process the file
        result = process_file(temp_filepath)

        # Add metadata to result
        result['filename'] = file.filename
        result['processed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Clean up temporary file
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception as e:
                print(f"Error removing temporary file: {e}")


@app.route('/download/csv')
def download_csv():
    """Generate and send CSV file."""
    try:
        data = request.args.get('data')
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Parse JSON data
        parsed_data = json.loads(data)
        if not isinstance(parsed_data, list):
            parsed_data = [parsed_data]

        # Create DataFrame
        df = pd.DataFrame(parsed_data)

        # Convert to CSV
        output = io.StringIO()
        df.to_csv(output, index=False)

        # Create response
        response = send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'invoice_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

        return response

    except Exception as e:
        return jsonify({'error': f'Error generating CSV: {str(e)}'}), 500


@app.route('/download/excel')
def download_excel():
    """Generate and send Excel file."""
    try:
        data = request.args.get('data')
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Parse JSON data
        parsed_data = json.loads(data)
        if not isinstance(parsed_data, list):
            parsed_data = [parsed_data]

        # Create DataFrame
        df = pd.DataFrame(parsed_data)

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Invoice Data', index=False)

        output.seek(0)

        # Create response
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'invoice_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

    except Exception as e:
        return jsonify({'error': f'Error generating Excel file: {str(e)}'}), 500


@app.errorhandler(413)
def too_large(e):
    """Handle file size exceeding limit."""
    return jsonify({
        'error': f'File is too large. Maximum size is {app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)}MB'
    }), 413


@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({
        'error': 'An internal server error occurred. Please try again.'
    }), 500


if __name__ == '__main__':
    app.run(debug=True)