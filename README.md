# 누니메모 (NuniMemo)

PySide6 기반의 데스크톱 메모 관리 애플리케이션

## 주요 기능

- 📝 **WYSIWYG 에디터**: 리치 텍스트 편집 지원
- 📁 **폴더 관리**: 계층적 폴더 구조
- 🔄 **Google Drive 동기화**: 클라우드 동기화 지원
- 🖼️ **이미지 지원**: 이미지 삽입 및 크기 조정
- 🎨 **모던 UI**: 깔끔한 사용자 인터페이스

## 설치 방법

### 사전 요구사항
- Python 3.8 이상
- Google Drive API 인증 정보

### 설치
```bash
# 클론
git clone https://github.com/knhanul/NuniMemo.git
cd NuniMemo

# 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 사용 방법

1. Google Drive 설정: `GOOGLE_DRIVE_SETUP.md` 참조
2. 앱 실행: `python main.py`

## 스크린샷

![메인 화면](https://raw.githubusercontent.com/knhanul/NuniMemo/main/screenshot.png)

## 기술 스택

- **UI**: PySide6 (Qt for Python)
- **디자인**: Qt Designer (.ui 파일)
- **데이터베이스**: SQLite
- **동기화**: Google Drive API
- **스타일링**: CSS 스타일시트

## 라이선스

MIT License
