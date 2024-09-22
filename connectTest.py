from pymongo import MongoClient
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# MongoDB 연결 문자열 구성
mongo_uri = f"mongodb://{os.getenv('MONGO_USERNAME')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_DB')}?authSource=admin"

client = MongoClient(mongo_uri)

try:
    # admin 데이터베이스에 대해 ping 명령 실행
    client.admin.command('ping')
    print("MongoDB에 성공적으로 연결되었습니다!")

    # boardlive 데이터베이스 선택
    db = client[os.getenv('MONGO_DB')]
    
    # 컬렉션 목록 출력
    print("데이터베이스의 컬렉션 목록:")
    collections = db.list_collection_names()
    for collection in collections:
        print(f"- {collection}")

    # qrcodes 컬렉션의 문서 수 출력
    qrcodes_count = db.qrcodes.count_documents({})
    print(f"qrcodes 컬렉션의 문서 수: {qrcodes_count}")

except Exception as e:
    print(f"MongoDB 연결 실패: {e}")

finally:
    # 연결 종료
    client.close()
