from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
import qrcode
from qrcode.image.svg import SvgPathImage
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 이 키를 안전한 랜덤 문자열로 변경하세요

# MongoDB 연결
client = MongoClient("mongodb://hangom:BoardLive99!@222.109.213.58:27017/boardlive?authSource=admin")
db = client.boardlive
qr_collection = db.qrcodes

# QR 코드 생성 함수
def generate_qr(data):
    # PNG 생성
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    png_img = qr.make_image(fill_color="black", back_color="white")
    png_buffer = io.BytesIO()
    png_img.save(png_buffer)
    png_str = base64.b64encode(png_buffer.getvalue()).decode()

    # SVG 생성
    svg_img = qr.make_image(image_factory=SvgPathImage)
    svg_buffer = io.BytesIO()
    svg_img.save(svg_buffer)
    svg_str = svg_buffer.getvalue().decode()

    return png_str, svg_str

@app.route('/')
def home():
    return render_template('register.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        title = request.form['title']
        url = request.form['url']
        qr_id = ObjectId()  # 새로운 ObjectId 생성
        qr_url = url_for('redirect_qr', qr_id=str(qr_id), _external=True)
        png_image, svg_image = generate_qr(qr_url)
        qr_collection.insert_one({
            '_id': qr_id,
            'title': title,
            'url': url,
            'png_image': png_image,
            'svg_image': svg_image
        })
        flash('QR 코드가 성공적으로 등록되었습니다.', 'success')
        return redirect(url_for('list_qr_codes'))
    return render_template('register.html')

@app.route('/list')
def list_qr_codes():
    qr_codes = qr_collection.find()
    return render_template('list.html', qr_codes=qr_codes)

@app.route('/delete/<string:qr_id>', methods=['POST'])
def delete_qr(qr_id):
    result = qr_collection.delete_one({'_id': ObjectId(qr_id)})
    if result.deleted_count > 0:
        flash('QR 코드가 성공적으로 삭제되었습니다.', 'success')
    else:
        flash('QR 코드 삭제에 실패했습니다.', 'error')
    return redirect(url_for('list_qr_codes'))

@app.route('/download/<string:qr_id>/<string:format>')
def download_qr(qr_id, format):
    qr_code = qr_collection.find_one({'_id': ObjectId(qr_id)})
    if qr_code:
        if format == 'png':
            image_data = base64.b64decode(qr_code['png_image'])
            mimetype = 'image/png'
            extension = 'png'
        elif format == 'svg':
            image_data = qr_code['svg_image'].encode()
            mimetype = 'image/svg+xml'
            extension = 'svg'
        else:
            flash('잘못된 형식입니다.', 'error')
            return redirect(url_for('list_qr_codes'))

        return send_file(
            io.BytesIO(image_data),
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"{qr_code['title']}.{extension}"
        )
    flash('QR 코드를 찾을 수 없습니다.', 'error')
    return redirect(url_for('list_qr_codes'))

@app.route('/edit/<string:qr_id>', methods=['GET', 'POST'])
def edit_qr(qr_id):
    qr_code = qr_collection.find_one({'_id': ObjectId(qr_id)})
    if not qr_code:
        flash('QR 코드를 찾을 수 없습니다.', 'error')
        return redirect(url_for('list_qr_codes'))

    if request.method == 'POST':
        title = request.form['title']
        url = request.form['url']
        qr_collection.update_one(
            {'_id': ObjectId(qr_id)},
            {'$set': {'title': title, 'url': url}}
        )
        flash('QR 코드가 성공적으로 수정되었습니다.', 'success')
        return redirect(url_for('list_qr_codes'))

    return render_template('edit.html', qr=qr_code)

@app.route('/qr/<string:qr_id>')
def redirect_qr(qr_id):
    qr_code = qr_collection.find_one({'_id': ObjectId(qr_id)})
    if qr_code:
        return redirect(qr_code['url'])
    flash('QR 코드를 찾을 수 없습니다.', 'error')
    return redirect(url_for('list_qr_codes'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333, debug=True)
