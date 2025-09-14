import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import anthropic

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

class ClaudeHandler:
    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    @staticmethod
    def get_credentials():
        SCOPES = ['https://www.googleapis.com/auth/drive.file']

        root_dir = Path(__file__).resolve().parents[1]
        token_path = root_dir / "token.json"
        creds_path = root_dir / "credentials.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return creds

    @staticmethod
    def upload_to_drive(local_file_path, file_name, folder_path="claude_generated_swift"):
        """
        Google Drive에 파일 업로드 (중첩 폴더 지원)
        folder_path 예시: "training_set/input_label" 또는 "training_set/class_label"
        """
        creds = ClaudeHandler.get_credentials()
        service = build('drive', 'v3', credentials=creds)

        # 폴더 경로를 '/'로 분리
        folder_parts = folder_path.split('/')
        current_folder_id = None

        # 각 폴더를 차례로 생성/찾기
        for folder_name in folder_parts:
            if current_folder_id:
                # 하위 폴더 검색
                query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{current_folder_id}' in parents and trashed=false"
            else:
                # 루트 폴더 검색
                query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

            response = service.files().list(q=query, fields="files(id, name)").execute()
            folders = response.get('files', [])

            if folders:
                current_folder_id = folders[0]['id']
            else:
                # 폴더 생성
                file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                if current_folder_id:
                    file_metadata['parents'] = [current_folder_id]

                folder = service.files().create(body=file_metadata, fields='id').execute()
                current_folder_id = folder.get('id')
                print(f"📁 Created Google Drive folder: {folder_name}")

        # 파일 업로드
        file_extension = os.path.splitext(file_name)[1].lower()
        if file_extension == '.swift':
            mimetype = 'text/x-swift'
        elif file_extension == '.json':
            mimetype = 'application/json'
        else:
            mimetype = 'text/plain'

        file_metadata = {'name': file_name, 'parents': [current_folder_id]}
        media = MediaFileUpload(local_file_path, mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"✅ Uploaded to Google Drive: {folder_path}/{file_name} (ID: {file.get('id')})")
        return file.get('id')

    @staticmethod
    def save_and_upload_analysis_result(swift_code_generated, json_label, repo_name, file_path):
        """분석 결과를 저장하고 Google Drive에 업로드"""
        try:
            # 파일명 생성
            safe_repo_name = repo_name.replace('/', '_').replace('-', '_')
            file_basename = os.path.splitext(os.path.basename(file_path))[0]
            module_name = repo_name.split('/')[-1]

            swift_filename = f"{safe_repo_name}_{file_basename}_example.swift"
            json_filename = f"{safe_repo_name}_{file_basename}_labels.json"

            # 임시 로컬 저장
            temp_dir = "./temp_analysis"
            os.makedirs(temp_dir, exist_ok=True)

            swift_local_path = os.path.join(temp_dir, swift_filename)
            json_local_path = os.path.join(temp_dir, json_filename)

            with open(swift_local_path, 'w', encoding='utf-8') as f:
                f.write(swift_code_generated)

            with open(json_local_path, 'w', encoding='utf-8') as f:
                f.write(json_label)

            # Google Drive 업로드
            # Swift 파일 → training_set/{input_label}/
            ClaudeHandler.upload_to_drive(
                local_file_path=swift_local_path,
                file_name=swift_filename,
                folder_path=f"training_set/input_label/{module_name}"  # input_label로 사용
            )

            # JSON 파일 → training_set/{class_label}/
            ClaudeHandler.upload_to_drive(
                local_file_path=json_local_path,
                file_name=json_filename,
                folder_path=f"training_set/class_label/{module_name}"  # class_label로 사용
            )

            # 임시 파일 삭제
            os.remove(swift_local_path)
            os.remove(json_local_path)

            print(f"      ☁️ Google Drive 업로드 완료")

        except Exception as e:
            print(f"      ❌ 저장/업로드 실패: {e}")



    @classmethod
    def ask(cls, prompt):
        response = cls.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

        # 2. Class Label (JSON 정답 레이블) 저장
        class_filename = f"{base_name}_label.json"
        class_filepath = os.path.join(local_dir, "class_label", class_filename)
        os.makedirs(os.path.dirname(class_filepath), exist_ok=True)

        with open(class_filepath, "w", encoding="utf-8") as f:
            f.write(json_label)
        print(f"📄 Class label saved: {class_filepath}")

        # 3. Google Drive에 훈련 데이터셋 구조로 업로드 (training_set 디렉토리 제외)
        ClaudeHandler.upload_to_drive(input_filepath, f"input_label/{input_filename}")
        ClaudeHandler.upload_to_drive(class_filepath, f"class_label/{class_filename}")

        print(f"☁️ Training data uploaded: {base_name}")

    @staticmethod
    def save_swift_code(code: str, library: str, context: str, local_dir: str = "./data/claude_generated_swift/"):
        os.makedirs(local_dir, exist_ok=True)
        filename = f"{library.lower()}_{context.lower().replace(' ', '_')}.swift"
        filepath = os.path.join(local_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"📄 Saved locally: {filepath}")

        # ClaudeHandler.upload_to_drive(filepath, filename)
