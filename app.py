from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import qrcode
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
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer)  # 'format' 인자 제거
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    return img_str

@app.route('/')
def home():
    return render_template('register.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        title = request.form['title']
        data = request.form['data']
        qr_image = generate_qr(data)
        qr_id = qr_collection.insert_one({'title': title, 'data': data, 'image': qr_image}).inserted_id
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333, debug=True)
