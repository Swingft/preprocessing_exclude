import json
from pathlib import Path
from tqdm import tqdm
import subprocess
import tempfile
import re
import concurrent.futures

import prompts
from gemini_handler.gemini_handler import GeminiHandler

# --- 테스트 전용 설정 (Test-only Configuration) ---
ANALYZER_EXECUTABLE = "./SwiftASTAnalyzer/.build/release/SwiftASTAnalyzer"
OUTPUT_DIR = Path("./output")

# 테스트 디렉토리 경로
TEST_BASE_DIR = OUTPUT_DIR / "generated_code" / "test"
TEST_INPUTS_BASE_DIR = OUTPUT_DIR / "inputs" / "test"
TEST_LABELS_BASE_DIR = OUTPUT_DIR / "outputs" / "test"


# 최종 테스트 데이터셋 파일들은 동적으로 생성됨


# --- 헬퍼 함수 (Helper Functions) ---

def run_swift_analyzer_on_code(swift_code: str) -> str | None:
    """Swift 코드를 분석하여 AST 정보를 JSON으로 반환합니다."""
    if not swift_code or not swift_code.strip():
        return None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.swift', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(swift_code)
            temp_file_path = temp_file.name

        command = [ANALYZER_EXECUTABLE, temp_file_path]
        process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=60)
        Path(temp_file_path).unlink()

        # 프로세스 실행 결과 확인
        if process.returncode != 0:
            print(f"  ⚠️ Swift analyzer exited with code {process.returncode}")
            if process.stderr:
                print(f"  ⚠️ Stderr: {process.stderr[:200]}...")
            return None

        # 출력이 비어있는지 확인
        if not process.stdout or not process.stdout.strip():
            print(f"  ⚠️ Swift analyzer returned empty output")
            return None

        # 로그 메시지를 제거하고 JSON 부분만 추출
        output = process.stdout.strip()

        # JSON이 시작되는 부분 찾기 (첫 번째 '{' 문자)
        json_start = output.find('{')
        if json_start == -1:
            print(f"  ⚠️ No JSON found in Swift analyzer output")
            return None

        # JSON 부분만 추출
        json_part = output[json_start:]

        # JSON 유효성 검사
        try:
            json.loads(json_part)
            return json_part
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Swift analyzer returned invalid JSON: {e}")
            print(f"  ⚠️ JSON part: {json_part[:200]}...")
            return None

    except subprocess.TimeoutExpired:
        print(f"  ⚠️ Swift analyzer timed out")
        if 'temp_file_path' in locals() and Path(temp_file_path).exists():
            Path(temp_file_path).unlink()
        return None
    except Exception as e:
        print(f"  ⚠️ Swift analyzer failed: {e}")
        if 'temp_file_path' in locals() and Path(temp_file_path).exists():
            Path(temp_file_path).unlink()
        return None


def extract_json_block(text: str) -> str | None:
    """텍스트에서 JSON 블록을 추출합니다."""
    if not text or not text.strip():
        return None

    # JSON 코드 블록에서 추출 시도
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            json.loads(json_str)  # 유효성 검사
            return json_str
        except json.JSONDecodeError:
            pass

    # 직접 JSON 형태인지 확인
    if text.strip().startswith("{"):
        try:
            json.loads(text.strip())  # 유효성 검사
            return text.strip()
        except json.JSONDecodeError:
            pass

    return None


def get_test_projects() -> list:
    """test 디렉토리 내의 모든 프로젝트 폴더를 지정된 순서로 반환합니다."""
    # 처리 순서 강제: UIKit+SPM_2 -> ConfettiSwiftUI -> iOS -> UIKit+SPM_1
    priority_order = [
        "Code_UIKit+SPM_2_combined",
        "Code_ConfettiSwiftUI",
        "Code_iOS",
        "Code_UIKit+SPM_1_combined"
    ]

    test_projects = []
    if TEST_BASE_DIR.exists():
        existing_projects = set()
        for item in TEST_BASE_DIR.iterdir():
            if item.is_dir():
                existing_projects.add(item.name)

        # 우선순위 순서대로 추가
        for project in priority_order:
            if project in existing_projects:
                test_projects.append(project)
                existing_projects.remove(project)

        # 나머지 프로젝트들은 알파벳 순으로 추가
        for project in sorted(existing_projects):
            test_projects.append(project)

    return test_projects


def get_test_project_paths(project_name: str) -> dict:
    """테스트 프로젝트의 디렉토리 경로를 반환합니다."""
    return {
        "code": TEST_BASE_DIR / project_name,
        "inputs": TEST_INPUTS_BASE_DIR / project_name,
        "labels": TEST_LABELS_BASE_DIR / project_name
    }


def is_valid_json_file(file_path: Path) -> bool:
    """JSON 파일이 유효한지 검사합니다."""
    try:
        if not file_path.exists() or file_path.stat().st_size <= 10:  # 최소 크기 체크
            return False
        content = file_path.read_text(encoding='utf-8').strip()
        if not content or content == "":
            return False
        json.loads(content)  # JSON 유효성 검사
        return True
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return False


# --- API 호출 함수 ---

def safe_gemini_label_request(prompt: str) -> str | None:
    """Gemini를 사용하여 라벨을 생성합니다."""
    print("    - Calling Gemini for label generation...")
    try:
        prompt_config = {"messages": [{"role": "user", "parts": [prompt]}]}
        response = GeminiHandler.ask(prompt_config, model_name="gemini-2.5-pro")

        if not response or not response.strip():
            return None

        json_str = extract_json_block(response)
        if not json_str:
            print(f"    ⚠️ Failed to extract valid JSON from response")
            return None

        # 한 번 더 유효성 검사
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            print(f"    ⚠️ Extracted JSON is invalid")
            return None

    except Exception as e:
        print(f"    ❌ Label generation request failed: {e}")
        return None


# --- 메인 처리 로직 ---

def discover_test_files():
    """모든 테스트 프로젝트에서 Swift 파일들을 발견합니다."""
    test_tasks = []
    test_projects = get_test_projects()

    print(f"📁 테스트 프로젝트들 검색 중...")

    for project in test_projects:
        project_code_dir = TEST_BASE_DIR / project
        if not project_code_dir.exists():
            print(f"  - {project}: 디렉토리가 존재하지 않습니다")
            continue

        swift_files = list(project_code_dir.glob("*.swift"))
        print(f"  - {project}: {len(swift_files)}개의 Swift 파일 발견")

        for swift_file in swift_files:
            task_name = swift_file.stem
            test_tasks.append({
                "project": project,
                "filename": task_name,
                "file_path": swift_file
            })

    return test_tasks


def process_test_sample(test_task: dict):
    """하나의 테스트 파일을 처리하여 라벨을 생성합니다."""
    project = test_task["project"]
    filename = test_task["filename"]
    file_path = test_task["file_path"]

    paths = get_test_project_paths(project)
    code_path = paths["code"] / f"{filename}.swift"
    input_path = paths["inputs"] / f"{filename}.txt"
    label_path = paths["labels"] / f"{filename}.json"

    # 이미 유효한 라벨이 있으면 스킵
    if is_valid_json_file(label_path):
        print(f"  - [TEST/{project}] `{filename}` - 이미 처리됨, 스킵")
        return

    print(f"  - [TEST/{project}] `{filename}` 처리 중...")

    # Swift 코드 읽기
    try:
        swift_code = code_path.read_text(encoding='utf-8')
        if not swift_code or not swift_code.strip():
            print(f"    ❌ Swift 코드가 비어있음")
            return
    except Exception as e:
        print(f"    ❌ Swift 코드 읽기 실패: {e}")
        return

    # AST 분석
    symbol_info_json = run_swift_analyzer_on_code(swift_code)
    if not symbol_info_json:
        print(f"    ❌ Swift analyzer 실패 또는 유효하지 않은 JSON 반환")
        return

    # 라벨 생성용 프롬프트 생성 및 저장
    try:
        label_prompt = prompts.GENERATE_LABEL_PROMPT.format(
            swift_code=swift_code,
            symbol_info_json=symbol_info_json
        )
        input_path.write_text(label_prompt, encoding='utf-8')
    except Exception as e:
        print(f"    ❌ 입력 프롬프트 저장 실패: {e}")
        return

    # 라벨 생성 (Gemini 2.5 Pro 사용)
    final_output_json_str = safe_gemini_label_request(label_prompt)
    if not final_output_json_str:
        print(f"    ❌ 유효한 라벨 생성 실패")
        try:
            label_path.write_text('{"error": "generation_failed"}', encoding='utf-8')
        except Exception:
            pass
        return

    # 최종 저장
    try:
        label_path.write_text(final_output_json_str, encoding='utf-8')
        print(f"    ✅ `{filename}` 처리 완료")
    except Exception as e:
        print(f"    ❌ 라벨 저장 실패: {e}")
        return


def assemble_test_datasets():
    """테스트 프로젝트별로 최종 데이터셋을 조립합니다."""
    print("\n📦 테스트 데이터셋 조립 중...")

    test_projects = get_test_projects()
    all_test_data = []
    project_counts = {}

    for project in test_projects:
        print(f"\n  - {project} 프로젝트 처리 중...")

        paths = get_test_project_paths(project)
        label_files = sorted(list(paths["labels"].glob("*.json")))

        if not label_files:
            print(f"    라벨 파일 없음")
            project_counts[project] = 0
            continue

        project_data = []
        success_count = 0
        error_count = 0

        for label_path in tqdm(label_files, desc=f"{project} 데이터셋 조립"):
            try:
                # 유효한 JSON 파일인지 확인
                if not is_valid_json_file(label_path):
                    error_count += 1
                    continue

                code_path = paths["code"] / (label_path.stem + ".swift")
                input_path = paths["inputs"] / (label_path.stem + ".txt")

                if not code_path.exists() or not input_path.exists():
                    error_count += 1
                    continue

                swift_code = code_path.read_text(encoding='utf-8')
                if not swift_code or not swift_code.strip():
                    error_count += 1
                    continue

                output_json_str = label_path.read_text(encoding='utf-8')
                input_prompt = input_path.read_text(encoding='utf-8')

                # input 프롬프트에서 symbol_info를 추출
                symbol_info_json = None
                if "symbol_info_json=" in input_prompt:
                    match = re.search(r'symbol_info_json=(.+?)(?=\n\n|\Z)', input_prompt, re.DOTALL)
                    if match:
                        symbol_info_json = match.group(1).strip()

                # 만약 추출에 실패하면 Swift analyzer 다시 실행
                if not symbol_info_json:
                    symbol_info_json = run_swift_analyzer_on_code(swift_code)
                    if not symbol_info_json:
                        error_count += 1
                        continue

                # JSON 파싱 검증
                try:
                    symbol_info_dict = json.loads(symbol_info_json)
                    output_dict = json.loads(output_json_str)
                except json.JSONDecodeError:
                    error_count += 1
                    continue

                # 최종 데이터셋 엔트리 생성
                entry = {
                    "instruction": "Identify which identifiers in the Swift code should be excluded from obfuscation based on the provided AST analysis, and provide detailed reasoning.",
                    "input": {
                        "swift_code": swift_code,
                        "symbol_info": symbol_info_dict
                    },
                    "output": output_dict
                }

                project_data.append(entry)
                all_test_data.append(entry)
                success_count += 1

            except Exception as e:
                error_count += 1
                print(f"\n⚠️ 파일 조립 중 에러 발생 '{label_path.name}': {e}")

        project_counts[project] = success_count
        print(f"    {success_count}개 성공, {error_count}개 실패")

        # 프로젝트별 데이터셋 파일 저장
        if project_data:
            try:
                project_dataset_file = OUTPUT_DIR / f"test_{project}_dataset.jsonl"
                with open(project_dataset_file, "w", encoding="utf-8") as f:
                    for entry in project_data:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"    저장됨: {project_dataset_file}")
            except Exception as e:
                print(f"    ❌ 프로젝트 데이터셋 저장 실패: {e}")

    # 전체 테스트 데이터셋 저장
    if all_test_data:
        try:
            all_test_dataset_file = OUTPUT_DIR / "all_test_dataset.jsonl"
            with open(all_test_dataset_file, "w", encoding="utf-8") as f:
                for entry in all_test_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"\n전체 테스트 데이터셋 저장됨: {all_test_dataset_file}")
        except Exception as e:
            print(f"\n❌ 전체 테스트 데이터셋 저장 실패: {e}")

    return project_counts, len(all_test_data)


def main_test_pipeline():
    """테스트 전용 메인 파이프라인"""
    print("🧪 테스트 전용 Swift 코드 처리 파이프라인 시작...")

    # 테스트 프로젝트별 디렉토리 생성
    test_projects = get_test_projects()
    if not test_projects:
        print("❌ 테스트 프로젝트를 찾을 수 없습니다!")
        print(f"   {TEST_BASE_DIR} 디렉토리에 프로젝트 폴더를 확인해주세요.")
        return

    print(f"발견된 테스트 프로젝트: {test_projects}")

    # 필요한 디렉토리 생성
    for project in test_projects:
        paths = get_test_project_paths(project)
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

    # 1. 테스트 파일들 발견
    test_tasks = discover_test_files()
    if not test_tasks:
        print("❌ 처리할 Swift 파일을 찾을 수 없습니다!")
        return

    print(f"\n총 {len(test_tasks)}개의 테스트 파일 발견")

    # 2. 병렬 처리로 샘플 생성
    print("\n🔄 테스트 파일들 처리 시작...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        list(tqdm(
            executor.map(process_test_sample, test_tasks),
            total=len(test_tasks),
            desc="테스트 파일 처리 중"
        ))

    # 3. 최종 데이터셋 조립
    project_counts, total_count = assemble_test_datasets()

    # 4. 결과 출력
    print(f"\n✨ 테스트 파이프라인 완료!")
    for project, count in project_counts.items():
        print(f"   - {project}: {count}개 데이터")
    print(f"   - 총 테스트 데이터: {total_count}개 생성 완료")

    # 저장된 파일들 정리
    print(f"\n📄 생성된 데이터셋 파일들:")
    for project in test_projects:
        if project_counts.get(project, 0) > 0:
            print(f"   - test_{project}_dataset.jsonl")
    if total_count > 0:
        print(f"   - all_test_dataset.jsonl")


if __name__ == "__main__":
    main_test_pipeline()