import os
import shutil
import filecmp
from pathlib import Path

SOURCE_DIRECTORIES = [
    Path("./Pods"),
    Path("./apple_sdk_headers")
]
DESTINATION_DIRECTORY = Path("./input_headers")


def find_and_copy_headers(src_dirs: list[Path], dest_dir: Path):
    """
    여러 소스 디렉토리에서 모든 .h 파일을 찾아 목적지 디렉토리로 복사합니다.
    파일 이름이 중복되지만 내용이 다를 경우, 파일명에 접미사를 붙여 저장합니다.

    Args:
        src_dirs (list[Path]): 검색을 시작할 소스 디렉토리 목록.
        dest_dir (Path): 헤더 파일을 복사할 목적지 디렉토리.
    """
    # 목적지 디렉토리 생성 (이미 존재하면 무시)
    dest_dir.mkdir(exist_ok=True)
    print(f"'{dest_dir}' 디렉토리를 확인/생성했습니다.")

    total_copied_count = 0
    total_header_files = 0

    for src_dir in src_dirs:
        print(f"\n{'=' * 60}")
        print(f"소스 디렉토리 '{src_dir}' 처리 중...")
        print(f"{'=' * 60}")

        if not src_dir.is_dir():
            print(f"경고: 소스 디렉토리 '{src_dir}'를 찾을 수 없습니다. 건너뜁니다.")
            continue

        # src_dir 내의 모든 .h 파일을 재귀적으로 검색
        header_files = list(src_dir.rglob("*.h"))

        if not header_files:
            print(f"'{src_dir}' 디렉토리에서 헤더 파일을 찾지 못했습니다.")
            continue

        print(f"'{src_dir}'에서 {len(header_files)}개의 헤더 파일을 찾았습니다. 복사를 시작합니다...")
        total_header_files += len(header_files)

        copied_count = 0
        for header_file in header_files:
            try:
                # 파일 이름이 중복될 수 있으므로, 소스 디렉토리 이름과 상위 디렉토리 이름을 포함하여 고유성을 높입니다.
                # 예: Pods/AFNetworking/AFNetworking.h -> Pods_AFNetworking_AFNetworking.h
                # 예: apple_sdk_headers/Foundation.h -> apple_sdk_headers_Foundation.h
                source_name = src_dir.name
                parent_name = header_file.parent.name if header_file.parent != src_dir else ""

                if parent_name and parent_name != source_name:
                    unique_name = f"{source_name}_{parent_name}_{header_file.name}"
                else:
                    unique_name = f"{source_name}_{header_file.name}"

                dest_path = dest_dir / unique_name

                # 만약 목적지에 파일이 이미 존재하면
                if dest_path.exists():
                    # 내용이 동일한지 확인합니다. (True이면 동일)
                    if filecmp.cmp(header_file, dest_path, shallow=False):
                        print(f"  - 내용이 동일하여 건너뛰기: {dest_path.name}")
                        continue
                    else:
                        # 내용이 다르면 새로운 이름(_1, _2, ...)을 찾습니다.
                        counter = 1
                        base_name = Path(unique_name).stem
                        extension = Path(unique_name).suffix
                        while True:
                            new_name = f"{base_name}_{counter}{extension}"
                            new_dest_path = dest_dir / new_name
                            if not new_dest_path.exists():
                                dest_path = new_dest_path
                                break
                            # 새로 만든 이름의 파일도 존재하고 내용까지 같다면 건너뛰기
                            elif filecmp.cmp(header_file, new_dest_path, shallow=False):
                                dest_path = None  # 복사하지 않음
                                print(f"  - 내용이 동일한 다른 이름의 파일({new_name})이 존재하여 건너뛰기")
                                break
                            counter += 1

                        if dest_path is None:
                            continue  # 복사하지 않기로 결정됨

                        print(f"  - 이름은 같지만 내용이 달라 새 이름으로 저장: {dest_path.name}")

                shutil.copy2(header_file, dest_path)
                print(f"  - 복사 완료: {header_file.name} -> {dest_path.name}")
                copied_count += 1
            except Exception as e:
                print(f"  - 복사 실패: {header_file.name}. 오류: {e}")

        print(f"'{src_dir}'에서 {copied_count}개의 파일을 복사했습니다.")
        total_copied_count += copied_count

    print(f"\n{'=' * 60}")
    print(f"전체 복사 작업 완료!")
    print(f"총 {total_header_files}개의 헤더 파일을 발견했고,")
    print(f"그 중 {total_copied_count}개의 새로운 파일을 '{dest_dir}'에 복사했습니다.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main_project_root = Path(__file__).resolve().parent
    source_paths = [main_project_root / src_dir for src_dir in SOURCE_DIRECTORIES]

    find_and_copy_headers(source_paths, main_project_root / DESTINATION_DIRECTORY)