import shutil
import re
from pathlib import Path

# 설정
SOURCE_DIRECTORY = Path("./input_headers")
PROCESSED_DIRECTORY = Path("./processed_headers")
SIZE_THRESHOLD_KB = 25
MIN_PART_SIZE_KB = 5


def find_safe_split_points(lines, threshold_bytes, min_part_bytes):
    """
    안전한 분할 지점들을 찾아 반환합니다.
    """
    split_points = []
    current_size = 0

    for i, line in enumerate(lines):
        current_size += len(line.encode('utf-8'))

        # 임계값의 70% 이상이면서 빈 줄인 경우 분할 후보
        if current_size >= threshold_bytes * 0.7 and not line.strip():
            # 안전한 분할 지점인지 확인
            if is_safe_split_location(lines, i):
                # 남은 내용이 너무 작지 않은지 확인
                remaining_content = "".join(lines[i + 1:])
                remaining_size = len(remaining_content.encode('utf-8'))

                if remaining_size == 0 or remaining_size >= min_part_bytes:
                    split_points.append(i + 1)  # 다음 줄부터 새 파트 시작
                    current_size = 0

        # 강제 분할 지점 (너무 커진 경우)
        elif current_size >= threshold_bytes * 1.3:
            split_points.append(i + 1)
            current_size = 0

    return split_points


def is_safe_split_location(lines, line_idx):
    """
    현재 위치가 안전한 분할 지점인지 확인합니다.
    """
    if line_idx >= len(lines) or lines[line_idx].strip():
        return False

    # 이전 3줄과 다음 3줄 확인
    start = max(0, line_idx - 3)
    end = min(len(lines), line_idx + 4)
    context_lines = [lines[i].strip() for i in range(start, end)]

    # 안전하지 않은 패턴들
    unsafe_patterns = [
        r'.*[,\\*]$',  # 계속되는 선언
        r'.*\($',  # 열린 괄호
        r'.*\{$',  # 열린 중괄호
        r'^\s*\*',  # 멀티라인 주석 중간
        r'^\s*(-->|<--)',  # Carbon 이벤트 파라미터
        r'.*Parameters:\s*$',
        r'.*Discussion:\s*$',
        r'.*Result:\s*$'
    ]

    # 이전 줄들 검사
    for i in range(max(0, line_idx - 2), line_idx):
        if i < len(lines):
            prev_line = lines[i].strip()
            if prev_line:
                for pattern in unsafe_patterns:
                    if re.search(pattern, prev_line):
                        return False

    # 안전한 종료 패턴들
    safe_end_patterns = [
        r'^\s*\*/\s*$',  # 주석 블록 종료
        r'^\s*#endif',  # endif
        r'^\s*};\s*$',  # 구조체/enum 종료
        r'.*;\s*$'  # 세미콜론 종료
    ]

    # 이전 줄이 안전한 종료 패턴인지 확인
    if line_idx > 0:
        prev_line = lines[line_idx - 1].strip()
        for pattern in safe_end_patterns:
            if re.search(pattern, prev_line):
                return True

    return False


def split_file_into_parts(file_path, threshold_bytes, min_part_bytes):
    """
    단일 파일을 여러 파트로 분할합니다.
    """
    # 여러 인코딩 시도
    content = None
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'mac-roman']:
        try:
            content = file_path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError(f"인코딩을 읽을 수 없습니다: {file_path.name}")

    lines = content.splitlines(keepends=True)
    split_points = find_safe_split_points(lines, threshold_bytes, min_part_bytes)

    # 분할 지점이 없으면 원본 그대로 반환
    if not split_points:
        return [content]

    parts = []
    start_idx = 0

    for split_point in split_points:
        part_content = "".join(lines[start_idx:split_point])
        if part_content.strip():  # 빈 파트는 제외
            parts.append(part_content)
        start_idx = split_point

    # 마지막 파트
    if start_idx < len(lines):
        final_part = "".join(lines[start_idx:])
        if final_part.strip():
            parts.append(final_part)

    return parts


def split_large_files():
    """
    큰 헤더 파일들을 분할합니다.
    """
    if not SOURCE_DIRECTORY.is_dir():
        print(f"오류: 소스 디렉토리 '{SOURCE_DIRECTORY}'를 찾을 수 없습니다.")
        return

    PROCESSED_DIRECTORY.mkdir(exist_ok=True)
    print(f"결과물을 저장할 '{PROCESSED_DIRECTORY}' 디렉토리를 생성했습니다.")

    threshold_bytes = SIZE_THRESHOLD_KB * 1024
    min_part_bytes = MIN_PART_SIZE_KB * 1024

    header_files = list(SOURCE_DIRECTORY.glob("*.h"))
    total_files = len(header_files)

    if total_files == 0:
        print("처리할 헤더 파일이 없습니다.")
        return

    print(f"총 {total_files}개의 헤더 파일을 검사합니다 (분할 기준: {SIZE_THRESHOLD_KB} KB).")

    copied_count = 0
    split_count = 0

    for i, header_path in enumerate(header_files):
        try:
            file_size = header_path.stat().st_size

            print(f"[{i + 1}/{total_files}] 처리 중: {header_path.name} ({file_size / 1024:.1f} KB)")

            # 작은 파일은 단순 복사
            if file_size <= threshold_bytes:
                shutil.copy2(header_path, PROCESSED_DIRECTORY / header_path.name)
                copied_count += 1
                print(f"  -> 복사 완료")
                continue

            # 큰 파일은 분할
            parts = split_file_into_parts(header_path, threshold_bytes, min_part_bytes)

            if len(parts) == 1:
                # 분할되지 않은 경우 원본 복사
                shutil.copy2(header_path, PROCESSED_DIRECTORY / header_path.name)
                copied_count += 1
                print(f"  -> 분할되지 않아 복사")
            else:
                # 분할된 경우 각 파트 저장
                for part_num, part_content in enumerate(parts, 1):
                    part_filename = f"{header_path.stem}_part{part_num}.h"
                    part_path = PROCESSED_DIRECTORY / part_filename
                    part_path.write_text(part_content, encoding="utf-8")
                    part_size = len(part_content.encode('utf-8')) / 1024
                    print(f"  -> 파트 {part_num}: {part_size:.1f} KB")

                split_count += 1
                print(f"  -> {len(parts)}개 파트로 분할 완료")

        except Exception as e:
            print(f"  -> 오류: {e}")

    print(f"\n처리 완료!")
    print(f"복사된 파일: {copied_count}개")
    print(f"분할된 파일: {split_count}개")


if __name__ == "__main__":
    split_large_files()