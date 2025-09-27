import json
from pathlib import Path

# --- 설정 ---
# 헤더 파일이 있는 디렉토리
INPUT_DIRECTORY = Path("./input_headers")

# 생성된 JSON 레이블이 있는 디렉토리
LABEL_DIRECTORY = Path("./output_labels")

# 최종 Alpaca 데이터셋을 저장할 파일 경로 (JSONL로 변경)
OUTPUT_FILE = Path("./header.jsonl")

# LoRA 학습에 사용할 일관된 지시문 (영문으로 수정됨)
# 이 지시문은 데이터셋의 모든 샘플에 동일하게 적용됩니다.
INSTRUCTION = "Extract all public API identifiers from the Objective-C header file that must be excluded from obfuscation."


# ---

def build_alpaca_dataset():
    """
    input_headers와 output_labels 디렉토리의 파일들을 조합하여
    LoRA 학습을 위한 Alpaca 형식의 최종 데이터셋을 생성합니다.
    """
    if not INPUT_DIRECTORY.is_dir() or not LABEL_DIRECTORY.is_dir():
        print(f"오류: '{INPUT_DIRECTORY}' 또는 '{LABEL_DIRECTORY}' 디렉토리를 찾을 수 없습니다.")
        print("'prepare_headers.py'와 'generate_labels.py'를 먼저 실행해주세요.")
        return

    print("Alpaca 데이터셋 생성을 시작합니다...")
    dataset_entries = 0

    # 레이블 파일을 기준으로 순회 (레이블이 성공적으로 생성된 파일만 처리)
    json_files = list(LABEL_DIRECTORY.glob("*.json"))
    total_files = len(json_files)

    if total_files == 0:
        print("처리할 레이블 파일이 없습니다. 'generate_labels.py'를 실행했는지 확인하세요.")
        return

    # 최종 데이터셋을 JSONL 파일로 저장
    try:
        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            for i, label_path in enumerate(json_files):
                header_name = label_path.with_suffix(".h").name
                header_path = INPUT_DIRECTORY / header_name

                if not header_path.exists():
                    print(f"  - [{i + 1}/{total_files}] ⚠️ 경고: 레이블 파일에 해당하는 헤더 파일을 찾을 수 없습니다. 건너뛰기: {header_path.name}")
                    continue

                try:
                    header_content = header_path.read_text(encoding="utf-8")
                    label_content_string = label_path.read_text(encoding="utf-8")

                    if not header_content.strip() or not label_content_string.strip():
                        print(f"  - [{i + 1}/{total_files}] ℹ️ 정보: 헤더 또는 레이블 파일 내용이 비어있어 건너뜁니다: {header_path.name}")
                        continue

                    json.loads(label_content_string)

                    data_entry = {
                        "instruction": INSTRUCTION,
                        "input": header_content,
                        "output": label_content_string
                    }

                    # 각 data_entry를 JSON 문자열로 변환하고 줄바꿈 문자와 함께 파일에 쓴다.
                    f.write(json.dumps(data_entry, ensure_ascii=False) + "\n")
                    dataset_entries += 1
                    print(f"  - [{i + 1}/{total_files}] ✅ 처리 완료: {header_path.name}")

                except json.JSONDecodeError:
                    print(f"  - [{i + 1}/{total_files}] ❌ 오류: JSON 레이블 파일이 손상되었습니다. 건너뛰기: {label_path.name}")
                except Exception as e:
                    print(f"  - [{i + 1}/{total_files}] ❌ 오류: 파일 처리 중 예상치 못한 오류 발생 ({header_path.name}): {e}")

        print(f"\n✅ 작업 완료! 총 {dataset_entries}개의 샘플을 '{OUTPUT_FILE}' 파일에 저장했습니다.")
    except Exception as e:
        print(f"\n❌ 최종 파일 저장 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    build_alpaca_dataset()

