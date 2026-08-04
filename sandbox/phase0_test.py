# FastAPI: 파이썬으로 웹 서버를 만드는 도구(프레임워크)
from fastapi import FastAPI
# FileResponse: 특정 파일의 내용을 그대로 응답으로 돌려주는 기능
from fastapi.responses import FileResponse

# app: 이 웹 서버 자체를 나타내는 객체. 앞으로 라우트(경로)들을 여기에 등록한다.
app = FastAPI()


# @app.get("/test") : 브라우저가 "/test" 경로로 GET 요청을 보내면
#                      바로 아래 함수(test)를 실행하라는 뜻
@app.get("/test")
def test():
    # 같은 폴더에 있는 phase0_test.html 파일을 읽어서 그대로 응답으로 보낸다
    return FileResponse("phase0_test.html")


# 이 파일을 직접 실행했을 때만(python test.py) 아래 코드가 동작한다
if __name__ == "__main__":
    # uvicorn: FastAPI 앱을 실제로 실행시켜주는 서버 프로그램
    import uvicorn

    # host="0.0.0.0" : 이 컴퓨터의 모든 네트워크 주소로 접속을 허용
    # port=8001      : 8001번 포트에서 요청을 기다림(listen)
    uvicorn.run(app, host="0.0.0.0", port=8001)
