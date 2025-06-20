from flask import Flask, render_template, request, redirect, flash
import os
import pandas as pd
import requests
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def dict_to_xml(submission_dict, xml_form_id, form_version):
    xml_parts = [f"<{key}>{value}</{key}>" for key, value in submission_dict.items()]
    xml_body = "".join(xml_parts)
    return f'<data id="{xml_form_id}" version="{form_version}">{xml_body}</data>'

def upload_to_odk_central(csv_file, base_url, project_id, xml_form_id, form_version, username, password):
    try:
        df = pd.read_csv(csv_file, encoding='ISO-8859-1')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_file, encoding='cp1252')

    # Authenticate with ODK Central
    session = requests.Session()
    auth_url = f"{base_url.rstrip('/')}/v1/sessions"
    auth_response = session.post(auth_url, json={'email': username, 'password': password})
    if auth_response.status_code != 200:
        raise Exception(f"Authentication failed: {auth_response.text}")

    token = auth_response.json()['token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/xml'
    }

    submission_url = f"{base_url.rstrip('/')}/v1/projects/{project_id}/forms/{xml_form_id}/submissions"

    # Submit each row
    for index, row in df.iterrows():
        submission_data = {col: row[col] for col in df.columns}
        xml_data = dict_to_xml(submission_data, xml_form_id, form_version)
        response = session.post(submission_url, headers=headers, data=xml_data)

        if response.status_code not in [200, 201]:
            print(f"❌ Row {index} failed: {response.text}")
        else:
            print(f"✅ Row {index} uploaded successfully")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        base_url = request.form['base_url']
        project_id = request.form['project_id']
        xml_form_id = request.form['xml_form_id']
        form_version = request.form['form_version']
        username = request.form['username']
        password = request.form['password']

        if csv_file:
            filename = secure_filename(csv_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            csv_file.save(file_path)

            try:
                upload_to_odk_central(
                    file_path, base_url, project_id,
                    xml_form_id, form_version,
                    username, password
                )
                flash("Upload process completed. Check the terminal for detailed output.", "success")
            except Exception as e:
                flash(f"Error: {str(e)}", "danger")

        return redirect('/')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
