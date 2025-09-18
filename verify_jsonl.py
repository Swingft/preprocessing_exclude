import json
import sys
from pathlib import Path


def analyze_json_structure(json_obj, line_number):
    """JSON 객체의 구조를 분석하여 문제점을 찾습니다."""
    issues = []

    # 필수 필드 확인
    if not isinstance(json_obj, dict):
        issues.append(f"Root is not a dictionary (type: {type(json_obj).__name__})")
        return issues

    # instruction 필드 확인
    if "instruction" not in json_obj:
        issues.append("Missing 'instruction' field")
    elif not isinstance(json_obj["instruction"], str):
        issues.append(f"'instruction' is not a string (type: {type(json_obj['instruction']).__name__})")

    # input 구조 확인
    if "input" in json_obj:
        if not isinstance(json_obj["input"], dict):
            issues.append(f"'input' is not a dictionary (type: {type(json_obj['input']).__name__})")

    # output 구조 확인 - 문자열 또는 딕셔너리 모두 허용
    if "output" in json_obj:
        output_type = type(json_obj["output"])
        if not isinstance(json_obj["output"], (str, dict)):
            issues.append(f"'output' is neither string nor dictionary (type: {output_type.__name__})")
        elif isinstance(json_obj["output"], dict):
            # 딕셔너리인 경우 예상되는 필드들 확인 (선택적)
            output_dict = json_obj["output"]
            if "reasoning" in output_dict and not isinstance(output_dict["reasoning"], str):
                issues.append(f"'output.reasoning' is not a string")
            if "exclusions" in output_dict and not isinstance(output_dict["exclusions"], list):
                issues.append(f"'output.exclusions' is not a list")

    return issues


def verify_jsonl_file(file_path: Path, detailed_analysis=False):
    """
    주어진 경로의 .jsonl 파일이 올바른 형식인지 검증하고 결과를 출력합니다.
    """
    if not file_path.exists():
        print(f"\n🟡 SKIPPING: File not found at '{file_path}'")
        return False

    print(f"\n{'=' * 60}")
    print(f"📁 Verifying file: {file_path}")

    # 파일 크기 확인
    file_size = file_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    print(f"📏 File size: {file_size_mb:.2f} MB")

    if file_size_mb > 10:
        print(f"⚠️  WARNING: Large file detected ({file_size_mb:.2f} MB)")

    valid_lines = 0
    invalid_lines = 0
    total_lines = 0
    empty_lines = 0
    structure_issues = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines += 1
                line_number = i + 1

                if not line.strip():
                    empty_lines += 1
                    continue

                try:
                    json_obj = json.loads(line)
                    valid_lines += 1

                    # 상세 분석이 요청되면 구조 검사
                    if detailed_analysis:
                        issues = analyze_json_structure(json_obj, line_number)
                        if issues:
                            structure_issues += 1
                            print(f"  🔍 Line {line_number} structure issues:")
                            for issue in issues:
                                print(f"    - {issue}")

                except json.JSONDecodeError as e:
                    invalid_lines += 1
                    print(f"  🔴 Line {line_number}: Invalid JSON")
                    print(f"    Error: {e}")
                    print(f"    Content preview: {line.strip()[:100]}...")

                    # 첫 10개 에러만 표시
                    if invalid_lines >= 10:
                        print(f"  ⚠️  ... (showing first 10 errors only)")
                        break

    except Exception as e:
        print(f"🔴 ERROR reading file: {e}")
        return False

    print("-" * 60)
    print(f"📊 SUMMARY:")
    print(f"  Total lines: {total_lines}")
    print(f"  Empty lines: {empty_lines}")
    print(f"  Valid JSON lines: {valid_lines}")
    print(f"  Invalid JSON lines: {invalid_lines}")
    if detailed_analysis and structure_issues > 0:
        print(f"  Structure issues: {structure_issues}")

    if invalid_lines == 0 and total_lines > 0:
        if structure_issues == 0 or not detailed_analysis:
            print("✅ SUCCESS: All lines are valid JSON objects.")
            return True
        else:
            print("⚠️  WARNING: JSON is valid but has structure issues.")
            return True
    elif total_lines == 0:
        print("🟡 WARNING: The file is empty.")
        return True
    else:
        print(f"❌ FAILURE: Found {invalid_lines} invalid JSON lines.")
        return False


if __name__ == "__main__":
    # 여러 디렉토리에서 검사
    directories_to_check = [
        Path("./output"),
        Path("./outputs")  # outputs 디렉토리도 추가
    ]

    # 검사할 파일 목록
    files_to_verify = [
        "claude_only_dataset.jsonl",
        "exclude.jsonl",
        "gemini_only_dataset.jsonl",
        "old_claude_dataset.jsonl",
        "old_gemini_dataset.jsonl"
    ]

    # 출력 디렉토리별로도 검사
    output_files = [
        "claude_generated",
        "gemini_generated",
        "old_claude_generated",
        "old_gemini_generated"
    ]

    print("🔍 JSONL File Verification Tool")
    print("=" * 60)

    all_good = True
    files_found = 0

    # 기본 output 디렉토리 검사
    for directory in directories_to_check:
        if not directory.exists():
            continue

        print(f"\n📂 Checking directory: {directory}")

        for filename in files_to_verify:
            path = directory / filename
            if path.exists():
                files_found += 1
                result = verify_jsonl_file(path, detailed_analysis=True)
                if not result:
                    all_good = False

        # outputs 디렉토리 내 하위 폴더들도 검사
        if directory.name == "outputs":
            for output_dir in output_files:
                subdir = directory / output_dir
                if subdir.exists() and subdir.is_dir():
                    print(f"\n📂 Checking subdirectory: {subdir}")
                    for jsonl_file in subdir.glob("*.jsonl"):
                        files_found += 1
                        result = verify_jsonl_file(jsonl_file, detailed_analysis=True)
                        if not result:
                            all_good = False

    print("\n" + "=" * 60)
    print(f"🏁 FINAL RESULT:")
    print(f"Files checked: {files_found}")
    if all_good:
        print("✅ All files are valid!")
    else:
        print("❌ Some files have issues that need attention.")
    print("=" * 60)