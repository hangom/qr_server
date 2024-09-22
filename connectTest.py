from pymongo import MongoClient

uri = "mongodb://hangom:BoardLive99!@222.109.213.58:27017/boardlive?authSource=admin"
client = MongoClient(uri)

try:
    client.admin.command('ping')
    print("MongoDB에 성공적으로 연결되었습니다!")
except Exception as e:
    print(f"MongoDB 연결 실패: {e}")
