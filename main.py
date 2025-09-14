import json
from pathlib import Path
from tqdm import tqdm
import random
import time
import subprocess
import tempfile
import re
import itertools
import concurrent.futures

import prompts
from gemini_handler.gemini_handler import GeminiHandler

# --- 설정 (Configuration) ---
ANALYZER_EXECUTABLE = "./SwiftASTAnalyzer/.build/release/SwiftASTAnalyzer"
RULES_FILE = "./obfuscation_rules.json"
SAFE_PATTERNS_FILE = "./obfuscation_safe_patterns.json"
OUTPUT_DIR = Path("./output")

# 생성기별 디렉토리 경로
GEMINI_CODE_DIR = OUTPUT_DIR / "generated_code" / "gemini_generated"
CLAUDE_CODE_DIR = OUTPUT_DIR / "generated_code" / "claude_generated"
GEMINI_INPUTS_DIR = OUTPUT_DIR / "inputs" / "gemini_generated"
CLAUDE_INPUTS_DIR = OUTPUT_DIR / "inputs" / "claude_generated"
GEMINI_LABELS_DIR = OUTPUT_DIR / "outputs" / "gemini_generated"
CLAUDE_LABELS_DIR = OUTPUT_DIR / "outputs" / "claude_generated"

# 최종 데이터셋 파일 경로
FINAL_DATASET_GEMINI_ONLY = OUTPUT_DIR / "gemini_only_dataset.jsonl"
FINAL_DATASET_CLAUDE_ONLY = OUTPUT_DIR / "claude_only_dataset.jsonl"
FINAL_DATASET_COMBINED = OUTPUT_DIR / "combined_dataset.jsonl"


# --- 헬퍼 함수 (Helper Functions) ---

def run_swift_analyzer_on_code(swift_code: str) -> str | None:
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


def get_generator_paths(generator_type: str) -> dict:
    """생성기 타입에 따라 올바른 디렉토리 경로를 반환합니다."""
    if generator_type == "gemini":
        return {
            "code": GEMINI_CODE_DIR,
            "inputs": GEMINI_INPUTS_DIR,
            "labels": GEMINI_LABELS_DIR
        }
    elif generator_type == "claude":
        return {
            "code": CLAUDE_CODE_DIR,
            "inputs": CLAUDE_INPUTS_DIR,
            "labels": CLAUDE_LABELS_DIR
        }
    else:
        raise ValueError(f"Unknown generator type: {generator_type}")


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


# --- API 호출 래퍼 함수 ---

def safe_gemini_code_request(prompt: str) -> str | None:
    print("    - Calling Gemini for code generation...")
    try:
        prompt_config = {"messages": [{"role": "user", "parts": [prompt]}]}
        response = GeminiHandler.ask(prompt_config, model_name="gemini-2.5-pro")

        if not response or not response.strip():
            return None

        # Swift 코드 블록 제거
        code = re.sub(r"^\s*```swift\s*", "", response, flags=re.MULTILINE)
        code = re.sub(r"\s*```\s*$", "", code, flags=re.MULTILINE)

        final_code = code.strip()
        return final_code if final_code else None

    except Exception as e:
        print(f"    ❌ Code generation request failed: {e}")
        return None


def safe_gemini_label_request(prompt: str) -> str | None:
    print("    - Calling Gemini for label generation...")
    try:
        prompt_config = {"messages": [{"role": "user", "parts": [prompt]}]}
        response = GeminiHandler.ask(prompt_config, model_name="gemini-1.5-pro-latest")

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


# --- 메인 파이프라인 로직 ---

def load_exclusion_rules(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)["obfuscation_exclusion_rules"]
    except Exception as e:
        print(f"❌ 규칙 파일 로드 실패 '{filepath}': {e}")
        exit(1)


def load_safe_patterns(filepath: str) -> list:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return [item["description"] for item in json.load(f)["safe_patterns"]]
    except Exception as e:
        print(f"❌ 안전한 패턴 파일 로드 실패 '{filepath}': {e}")
        return []


def create_generation_tasks(rules: dict) -> list:
    print("🧠 Generating comprehensive task list...")
    tasks = []

    all_l2_patterns = []
    for l1, l1_content in rules.items():
        for l2, l2_content in l1_content.get("L2_Patterns", {}).items():
            l2_content.update({"l1_reason": l1, "l2_pattern": l2})
            all_l2_patterns.append(l2_content)

    for pattern in all_l2_patterns:
        rules_content = pattern.get("sufficiency_rules", {})

        # Sufficient combinations
        for i, combo in enumerate(rules_content.get("sufficient_combinations", [])):
            tasks.append({
                "type": "Sufficient_Positive",
                "content": {"pattern": pattern, "evidence": combo},
                "filename": f"{pattern['l1_reason']}_{pattern['l2_pattern']}_sufficient_{i}"
            })

        # Insufficient evidence
        for i, evidence in enumerate(rules_content.get("insufficient_single_evidence", [])):
            tasks.append({
                "type": "Insufficient_Positive",
                "content": {"pattern": pattern, "evidence": [evidence]},
                "filename": f"{pattern['l1_reason']}_{pattern['l2_pattern']}_insufficient_{i}"
            })

        # Negative cases
        tasks.append({
            "type": "Clear_Negative",
            "content": {"pattern": pattern},
            "filename": f"{pattern['l1_reason']}_{pattern['l2_pattern']}_negative"
        })

    # Combined patterns
    for p1, p2 in itertools.combinations(all_l2_patterns, 2):
        filename = f"COMBINED_{p1['l2_pattern']}_{p2['l2_pattern']}"
        tasks.append({
            "type": "Combined_Positive",
            "content": {"pattern1": p1, "pattern2": p2},
            "filename": filename
        })

    print(f"✅ Task list generated. Total unique tasks: {len(tasks)}")
    return tasks


def process_and_save_sample(task_info: tuple):
    task, generator_type, safe_patterns = task_info

    task_type = task["type"]
    content = task["content"]
    filename = task["filename"]

    paths = get_generator_paths(generator_type)
    code_path = paths["code"] / f"{filename}.swift"
    input_path = paths["inputs"] / f"{filename}.txt"
    label_path = paths["labels"] / f"{filename}.json"

    # 이미 유효한 라벨이 있으면 스킵
    if is_valid_json_file(label_path):
        return

    print(f"  - [{generator_type.upper()}] `{filename}` ({task_type}) 샘플 생성 중...")

    # 1. Swift 코드 생성/로드
    swift_code = ""
    if code_path.exists() and code_path.stat().st_size > 50:  # 최소 크기 체크
        try:
            swift_code = code_path.read_text(encoding='utf-8')
        except Exception:
            swift_code = ""

    if not swift_code or not swift_code.strip():
        if generator_type == "gemini":
            code_gen_func = safe_gemini_code_request
        else:
            print(f"    ⚠️ Skipping {generator_type} - not implemented")
            return

        # 프롬프트 생성
        if task_type == "Sufficient_Positive":
            prompt = prompts.GENERATE_SUFFICIENT_POSITIVE_CODE_PROMPT.format(
                pattern_description=content['pattern']['description'],
                evidence_list=json.dumps(content['evidence'])
            )
        elif task_type == "Insufficient_Positive":
            prompt = prompts.GENERATE_INSUFFICIENT_POSITIVE_CODE_PROMPT.format(
                pattern_description=content['pattern']['description'],
                evidence_list=json.dumps(content['evidence'])
            )
        elif task_type == "Clear_Negative":
            prompt = prompts.GENERATE_NEGATIVE_CODE_PROMPT.format(
                pattern_description=content['pattern']['description']
            )
        elif task_type == "Combined_Positive":
            p1, p2 = content['pattern1'], content['pattern2']
            p1_evidence = p1.get('sufficiency_rules', {}).get('sufficient_combinations', [[]])[0]
            p2_evidence = p2.get('sufficiency_rules', {}).get('sufficient_combinations', [[]])[0]
            prompt = prompts.GENERATE_COMBINED_CODE_PROMPT.format(
                pattern1_description=p1['description'],
                pattern1_evidence=json.dumps(p1_evidence),
                pattern2_description=p2['description'],
                pattern2_evidence=json.dumps(p2_evidence)
            )
        else:
            print(f"    ⚠️ Unknown task type: {task_type}")
            return

        swift_code = code_gen_func(prompt)
        if not swift_code or not swift_code.strip():
            print(f"    ❌ Failed to generate Swift code")
            return

        # 코드 저장
        try:
            code_path.write_text(swift_code, encoding='utf-8')
        except Exception as e:
            print(f"    ❌ Failed to save code: {e}")
            return

    # 2. Swift 분석기 실행
    symbol_info_json = run_swift_analyzer_on_code(swift_code)
    if not symbol_info_json:
        print(f"    ❌ Swift analyzer failed or returned invalid JSON")
        return

    # 3. 라벨 생성 프롬프트 저장
    try:
        label_prompt = prompts.GENERATE_LABEL_PROMPT.format(
            swift_code=swift_code,
            symbol_info_json=symbol_info_json
        )
        input_path.write_text(label_prompt, encoding='utf-8')
    except Exception as e:
        print(f"    ❌ Failed to save input prompt: {e}")
        return

    # 4. 라벨 생성 및 저장
    final_output_json_str = safe_gemini_label_request(label_prompt)
    if not final_output_json_str:
        print(f"    ❌ Failed to generate valid label")
        # 빈 파일 대신 실패 표시 저장
        try:
            label_path.write_text('{"error": "generation_failed"}', encoding='utf-8')
        except Exception:
            pass
        return

    try:
        label_path.write_text(final_output_json_str, encoding='utf-8')
        print(f"    ✅ Saved artifacts for `{filename}`.")
    except Exception as e:
        print(f"    ❌ Failed to save label: {e}")


def assemble_final_dataset():
    print("\n📦 최종 데이터셋 조립 중...")
    datasets = {"gemini": [], "claude": [], "combined": []}

    for generator in ["gemini", "claude"]:
        paths = get_generator_paths(generator)
        label_files = sorted(list(paths["labels"].glob("*.json")))
        if not label_files:
            print(f"  - {generator.capitalize()}: 라벨 파일 없음")
            continue

        success_count = 0
        error_count = 0

        for label_path in tqdm(label_files, desc=f"{generator.capitalize()} 데이터셋 조립"):
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

                # input 프롬프트에서 symbol_info를 추출 (이미 생성된 것 사용)
                symbol_info_json = None
                if "symbol_info_json=" in input_prompt:
                    # 프롬프트에서 symbol_info 부분 추출
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

                datasets[generator].append(entry)
                datasets["combined"].append(entry)
                success_count += 1

            except Exception as e:
                error_count += 1
                print(f"\n⚠️ 파일 조립 중 에러 발생 '{label_path.name}': {e}")

        print(f"  - {generator.capitalize()}: {success_count}개 성공, {error_count}개 실패")

    # 최종 데이터셋 파일 저장
    try:
        with open(FINAL_DATASET_GEMINI_ONLY, "w", encoding="utf-8") as f:
            for entry in datasets["gemini"]:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        with open(FINAL_DATASET_CLAUDE_ONLY, "w", encoding="utf-8") as f:
            for entry in datasets["claude"]:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        with open(FINAL_DATASET_COMBINED, "w", encoding="utf-8") as f:
            for entry in datasets["combined"]:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"❌ 최종 데이터셋 저장 실패: {e}")

    return {name: len(ds) for name, ds in datasets.items()}


def main_pipeline():
    # 디렉토리 생성
    for gen in ["gemini", "claude"]:
        paths = get_generator_paths(gen)
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

    print("🚀 난독화 제외 데이터셋 생성 파이프라인 시작...")

    # 규칙 및 패턴 로드
    rules = load_exclusion_rules(RULES_FILE)
    safe_patterns = load_safe_patterns(SAFE_PATTERNS_FILE)
    tasks = create_generation_tasks(rules)

    GENERATORS_TO_RUN = ["gemini"]

    # 태스크 리스트 생성
    full_task_list = []
    for gen_type in GENERATORS_TO_RUN:
        for task in tasks:
            full_task_list.append((task, gen_type, safe_patterns))

    print(f"총 {len(full_task_list)}개 태스크 처리 시작...")

    # 병렬 처리로 샘플 생성
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:  # 동시 요청 수 줄임
        list(tqdm(
            executor.map(process_and_save_sample, full_task_list),
            total=len(full_task_list),
            desc="전체 태스크 처리 중"
        ))

    # 최종 데이터셋 조립
    counts = assemble_final_dataset()

    print(f"\n✨ 파이프라인 종료!")
    print(f"   - Gemini 데이터: {counts['gemini']}개, Claude 데이터: {counts['claude']}개, 총 {counts['combined']}개 생성 완료.")


if __name__ == "__main__":
    main_pipeline()