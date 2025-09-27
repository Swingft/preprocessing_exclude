import json
from pathlib import Path

# --- 설정 ---
# 헤더 파일이 있는 디렉토리 (분할 처리된 파일들)
INPUT_DIRECTORY = Path("./processed_headers")

# 생성된 JSON 레이블이 있는 디렉토리
LABEL_DIRECTORY = Path("./output_labels")

# 최종 Alpaca 데이터셋을 저장할 파일 경로 (JSONL로 변경)
OUTPUT_FILE = Path("./header.jsonl")

# LoRA 학습에 사용할 일관된 지시문 (영문으로 수정됨)
# 이 지시문은 데이터셋의 모든 샘플에 동일하게 적용됩니다.
INSTRUCTION = "Extract all public API identifiers from the Objective-C header file that must be excluded from obfuscation."


# ---

def read_file_with_encoding(file_path: Path) -> str:
    """
    여러 인코딩을 시도해서 파일을 읽습니다.
    """
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'mac-roman']:
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"모든 인코딩으로 파일을 읽을 수 없습니다: {file_path.name}")


def build_alpaca_dataset():
    """
    processed_headers 디렉토리의 헤더 파일들과 해당하는 output_labels의 JSON 파일들을 조합하여
    LoRA 학습을 위한 Alpaca 형식의 최종 데이터셋을 생성합니다.
    """
    if not INPUT_DIRECTORY.is_dir():
        print(f"오류: '{INPUT_DIRECTORY}' 디렉토리를 찾을 수 없습니다.")
        print("먼저 split_large_headers.py를 실행해주세요.")
        return

    if not LABEL_DIRECTORY.is_dir():
        print(f"오류: '{LABEL_DIRECTORY}' 디렉토리를 찾을 수 없습니다.")
        print("먼저 generate_labels.py를 실행해주세요.")
        return

    print("Alpaca 데이터셋 생성을 시작합니다...")
    dataset_entries = 0

    # 헤더 파일을 기준으로 순회 (processed_headers에 모든 파일이 있음)
    header_files = list(INPUT_DIRECTORY.glob("*.h"))
    total_files = len(header_files)

    if total_files == 0:
        print("처리할 헤더 파일이 없습니다. split_large_headers.py를 실행했는지 확인하세요.")
        return

    print(f"총 {total_files}개의 헤더 파일을 발견했습니다.")

    # 최종 데이터셋을 JSONL 파일로 저장
    try:
        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            for i, header_path in enumerate(header_files):
                # 해당하는 레이블 파일 경로
                label_name = header_path.with_suffix(".json").name
                label_path = LABEL_DIRECTORY / label_name

                if not label_path.exists():
                    print(f"  - [{i + 1}/{total_files}] ⚠️ 경고: 레이블 파일을 찾을 수 없습니다. 건너뛰기: {label_name}")
                    continue

                try:
                    # 다중 인코딩 지원으로 파일 읽기
                    header_content = read_file_with_encoding(header_path)
                    label_content_string = label_path.read_text(encoding="utf-8")

                    if not header_content.strip() or not label_content_string.strip():
                        print(f"  - [{i + 1}/{total_files}] ℹ️ 정보: 헤더 또는 레이블 파일 내용이 비어있어 건너뜁니다: {header_path.name}")
                        continue

                    # JSON 형식이 올바른지 검증
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

                except UnicodeDecodeError as e:
                    print(f"  - [{i + 1}/{total_files}] ❌ 인코딩 오류: {header_path.name} - {e}")
                except json.JSONDecodeError:
                    print(f"  - [{i + 1}/{total_files}] ❌ 오류: JSON 레이블 파일이 손상되었습니다. 건너뛰기: {label_path.name}")
                except Exception as e:
                    print(f"  - [{i + 1}/{total_files}] ❌ 오류: 파일 처리 중 예상치 못한 오류 발생 ({header_path.name}): {e}")

        print(f"\n✅ 작업 완료! 총 {dataset_entries}개의 샘플을 '{OUTPUT_FILE}' 파일에 저장했습니다.")
        print(f"성공률: {dataset_entries}/{total_files} ({dataset_entries / total_files * 100:.1f}%)")

        if dataset_entries < total_files:
            missing_labels = total_files - dataset_entries
            print(f"\n📝 참고: {missing_labels}개의 헤더 파일에 대한 레이블이 누락되었습니다.")
            print("누락된 파일들에 대해 generate_labels.py를 다시 실행해보세요.")

        # 분할된 파일들에 대한 정보 제공
        part_files = [f for f in header_files if "_part" in f.name]
        if part_files:
            print(f"\n📄 분할된 파일: {len(part_files)}개 (전체 {len(header_files)}개 중)")
            original_files = len(header_files) - len(part_files)
            print(f"📄 원본 파일: {original_files}개")

    except Exception as e:
        print(f"\n❌ 최종 파일 저장 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    build_alpaca_dataset()