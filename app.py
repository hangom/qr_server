from flask import Flask, request, render_template, redirect, url_for, flash, send_file, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.svg import SvgPathImage
from PIL import Image
import io
import base64
from dotenv import load_dotenv
import os
import xml.etree.ElementTree as ET
import re
from werkzeug.utils import secure_filename
import urllib.parse
from bson.binary import Binary
import logging
from werkzeug.exceptions import BadRequest
from logging.handlers import RotatingFileHandler

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads'  

# UPLOAD_FOLDER 생성
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# MongoDB 연결 문자열 성
mongo_uri = f"mongodb://{os.getenv('MONGO_USERNAME')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_DB')}?authSource=admin"

client = MongoClient(mongo_uri)
db = client[os.getenv('MONGO_DB')]
qr_collection = db.qrcodes

# QR 드 생성 함수
def generate_qr_with_logo(url, logo_path):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    logo = Image.open(logo_path).convert('RGBA')

    # 로고 크기 조정 (QR 코드의 25%로)
    logo_size = int(qr_image.size[0] * 0.25)
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # 로고 위치 계산
    position = ((qr_image.size[0] - logo.size[0]) // 2, (qr_image.size[1] - logo.size[1]) // 2)

    # 로고 붙이기
    qr_image.paste(logo, position, logo)

    # PNG 이미지를 바이트로 변환
    png_image = io.BytesIO()
    qr_image.save(png_image, format='PNG')
    png_bytes = png_image.getvalue()

    # SVG 생성
    svg_image = qr.make_image(image_factory=qrcode.image.svg.SvgImage).to_string().decode('utf-8')

    return png_bytes, svg_image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# secure_filename 함수를 수정합니다.
def secure_filename(filename):
    filename = urllib.parse.unquote(filename)
    return ''.join(c for c in filename if c.isalnum() or c in '._- ')

@app.route('/')
def home():
    return render_template('register.html', allowed_extensions=list(ALLOWED_EXTENSIONS))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', allowed_extensions=list(ALLOWED_EXTENSIONS))
    
    if request.method == 'POST':
        try:
            app.logger.debug("Starting QR code registration process")
            title = request.form.get('title', '제목 없음')
            data_type = request.form.get('data_type', '알 수 없음')
            qr_id = ObjectId()

            app.logger.debug(f"Title: {title}, Data Type: {data_type}")

            if data_type == 'URL':
                data = request.form.get('url', '')
            elif data_type in ['Image', 'FILE']:
                file = request.files.get('file')
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_data = file.read()
                    mime_type = file.content_type
                    data = {
                        'filename': filename,
                        'data': base64.b64encode(file_data).decode('utf-8'),
                        'mime_type': mime_type
                    }
                else:
                    flash('허용되지 않는 파일 형식입니다.', 'error')
                    return redirect(url_for('register'))
            elif data_type == 'Text':
                data = request.form.get('text', '')
            else:
                data = ''

            app.logger.debug(f"Data: {data}")

            qr_url = url_for('redirect_qr', qr_id=str(qr_id), _external=True)
            logo_path = os.path.join(app.static_folder, 'logo.png')
            app.logger.debug(f"QR URL: {qr_url}, Logo Path: {logo_path}")

            png_image, svg_image = generate_qr_with_logo(qr_url, logo_path)
            app.logger.debug(f"PNG Image Type: {type(png_image)}, SVG Image Type: {type(svg_image)}")

            qr_data = {
                '_id': qr_id,
                'title': title,
                'data_type': data_type,
                'data': data,
                'png_image': base64.b64encode(png_image).decode('utf-8'),
                'svg_image': svg_image
            }
            app.logger.debug("Inserting QR code data into database")
            qr_collection.insert_one(qr_data)

            app.logger.debug("QR code registration successful")
            flash('QR 코드가 성공적으로 등록되었습니다.', 'success')
            return redirect(url_for('list_qr_codes'))
        except Exception as e:
            app.logger.error(f"Error in register function: {str(e)}")
            app.logger.exception("Exception details:")
            flash('QR 코드 등록 중 오류가 발생했습니다.', 'error')
            return redirect(url_for('register'))

@app.route('/list')
def list_qr_codes():
    qr_codes = list(qr_collection.find())
    processed_qr_codes = []
    for qr in qr_codes:
        processed_qr = {
            '_id': str(qr.get('_id', '')),
            'title': qr.get('title', '제목 없음'),
            'data_type': qr.get('data_type', '알 수 없음'),
            'data': qr.get('data', ''),
            'png_image': qr.get('png_image', ''),
            'svg_image': qr.get('svg_image', '')
        }
        if processed_qr['data_type'] in ['Image', 'FILE'] and isinstance(processed_qr['data'], dict):
            if 'data' in processed_qr['data']:
                try:
                    if isinstance(processed_qr['data']['data'], bytes):
                        processed_qr['data']['data'] = base64.b64encode(processed_qr['data']['data']).decode('utf-8')
                except Exception as e:
                    app.logger.error(f"Error encoding data for QR code {processed_qr['_id']}: {str(e)}")
                    processed_qr['data']['data'] = ''
        processed_qr_codes.append(processed_qr)
    return render_template('list.html', qr_codes=processed_qr_codes)

@app.route('/delete/<qr_id>', methods=['POST'])
def delete_qr(qr_id):
    qr_collection.delete_one({'_id': ObjectId(qr_id)})
    flash('QR 코드가 삭제되었습니다.', 'success')
    return redirect(url_for('list_qr_codes'))

@app.route('/download/<qr_id>/<format>', methods=['GET'])
def download_qr(qr_id, format):
    qr_code = qr_collection.find_one({'_id': ObjectId(qr_id)})
    if not qr_code:
        flash('QR 코드를 찾을 수 없습니다.', 'error')
        return redirect(url_for('list_qr_codes'))

    if format == 'png':
        image_data = base64.b64decode(qr_code['png_image'])
        mimetype = 'image/png'
        filename = f"qr_code_{qr_id}.png"
    elif format == 'svg':
        image_data = qr_code['svg_image'].encode('utf-8')
        mimetype = 'image/svg+xml'
        filename = f"qr_code_{qr_id}.svg"
    else:
        flash('지원하지 않는 형식입니다.', 'error')
        return redirect(url_for('list_qr_codes'))

    return send_file(
        io.BytesIO(image_data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )

@app.route('/download_file/<string:qr_id>')
def download_file(qr_id):
    qr_code = qr_collection.find_one({'_id': ObjectId(qr_id)})
    if qr_code and qr_code['data_type'] in ['Image', 'FILE']:  # 여기를 수정
        file_data = qr_code['data']
        return send_file(
            io.BytesIO(base64.b64decode(file_data['data'])),
            mimetype=file_data['mime_type'],
            as_attachment=True,
            download_name=file_data['filename']
        )
    flash('파일을 찾을 수 없습니다.', 'error')
    return redirect(url_for('list_qr_codes'))

@app.route('/edit/<qr_id>', methods=['GET', 'POST'])
def edit_qr(qr_id):
    qr = qr_collection.find_one({'_id': ObjectId(qr_id)})
    if not qr:
        flash('QR 코드를 찾을 수 없습니다.', 'error')
        return redirect(url_for('list_qr_codes'))

    if request.method == 'POST':
        title = request.form.get('title')
        data_type = qr['data_type']

        if data_type == 'URL':
            data = request.form.get('url')
        elif data_type == 'Text':
            data = request.form.get('text')
        elif data_type in ['Image', 'FILE']:
            file = request.files.get('file')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_data = file.read()
                mime_type = file.content_type
                data = {
                    'filename': filename,
                    'data': base64.b64encode(file_data).decode('utf-8'),
                    'mime_type': mime_type
                }
            else:
                data = qr['data']  # 파일이 제공되지 않으면 기존 데이터를 유지합니다.

        # QR 코드 이미지는 변경하지 않고 기존 이미지를 유지합니다.
        png_image = qr['png_image']
        svg_image = qr['svg_image']

        # 데이터베이스 업데이트
        qr_collection.update_one({'_id': ObjectId(qr_id)}, {'$set': {
            'title': title,
            'data': data,
            'png_image': png_image,
            'svg_image': svg_image
        }})

        flash('QR 코드가 수정되었습니다.', 'success')
        return redirect(url_for('list_qr_codes'))

    return render_template('edit_qr.html', qr=qr)

@app.route('/qr/<qr_id>')
def redirect_qr(qr_id):
    qr_code = qr_collection.find_one({'_id': ObjectId(qr_id)})
    if not qr_code:
        flash('QR 코드를 찾을 수 없습니다.', 'error')
        return redirect(url_for('list_qr_codes'))

    if qr_code['data_type'] == 'URL':
        return redirect(qr_code['data'])
    elif qr_code['data_type'] in ['Image', 'FILE']:
        file_data = qr_code['data']
        return send_file(
            io.BytesIO(base64.b64decode(file_data['data'])),
            mimetype=file_data['mime_type'],
            as_attachment=True,
            download_name=file_data['filename']
        )
    elif qr_code['data_type'] == 'Text':
        return render_template('text_view.html', text=qr_code['data'])
    else:
        flash('지원하지 않는 데이터 유형입니다.', 'error')
        return redirect(url_for('list_qr_codes'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# b64encode 필터 추가
@app.template_filter('b64encode')
def b64encode_filter(data):
    if isinstance(data, bytes):
        return base64.b64encode(data).decode('utf-8')
    return ''

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    app.logger.error(f'Bad request: {e}')
    return '잘못된 요청입니다.', 400

if __name__ == '__main__':
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    # 외부 접속 가능하도록 호스트를 '0.0.0.0'으로 설정하고 포트를 3333으로 지정
    app.run(host='0.0.0.0', port=3333, debug=True)
