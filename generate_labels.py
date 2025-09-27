import json
import time
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from gemini_handler.gemini_handler import GeminiHandler, GeminiBlockedError, GeminiResponseEmptyError

# --- 설정 ---
# 준비된 헤더 파일이 있는 입력 디렉토리
INPUT_DIRECTORY = Path("./input_headers")

# 생성된 정답 레이블(JSON)을 저장할 출력 디렉토리
OUTPUT_DIRECTORY = Path("./output_labels")

# 사용할 Gemini 모델 이름
MODEL_NAME = "gemini-2.5-pro"

# 병렬 처리 설정
MAX_WORKERS = 10  # 동시에 처리할 스레드 수
BATCH_SIZE = 50  # 한 번에 처리할 파일 수
REQUEST_DELAY = 0.1  # API 요청 간 딜레이 (초)
MAX_RETRIES = 3  # 실패 시 최대 재시도 횟수

# ---

# Gemini API에 전송할 프롬프트 템플릿 (기존과 동일)
PROMPT_TEMPLATE = """
## ROLE & GOAL
You are a high-precision static code analyzer specializing in Objective-C. Your SOLE task is to parse the provided Objective-C header file content and extract a definitive list of all public API identifiers that MUST be excluded from code obfuscation. Accuracy is critical, as any error will break the client application.

## CRITICAL RULES FOR IDENTIFIER EXTRACTION
You MUST strictly adhere to the following rules. Do not deviate.

1.  **@interface:** Extract the class name.
    -   Example: `@interface MyClass : NSObject` -> `MyClass`

2.  **Method Selectors:** Extract the FULL selector for methods starting with `+` or `-`. The selector includes ALL parts of the name and ALL colons. The final colon is MANDATORY if the last part takes an argument.
    -   Example: `- (void)doSomethingWith:(id)arg1 andAnotherThing:(id)arg2;` -> `doSomethingWith:andAnotherThing:`
    -   Example: `- (id)someValue;` -> `someValue`

3.  **Macros (`#define`):** Extract names of simple, value-based macros. IGNORE function-like macros that take arguments.
    -   Example: `#define MyConstant 123` -> `MyConstant`
    -   Example to IGNORE: `#define MyMacro(a, b) (a+b)`

4.  **Type Definitions (`typedef`):** Extract the final type alias. This includes `typedef struct`, `typedef enum`, and block types.
    -   Example: `typedef void (^MyCompletionBlock)(BOOL success);` -> `MyCompletionBlock`
    -   Example: `typedef NS_ENUM(NSInteger, MyEnumType)` -> `MyEnumType`

5.  **Enum Cases:** From `NS_ENUM` or `typedef enum`, extract ALL individual case names.
    -   Example: `typedef NS_ENUM(NSInteger, MyEnum) {{ MyEnumCaseOne, MyEnumCaseTwo }};` -> `MyEnum`, `MyEnumCaseOne`, `MyEnumCaseTwo`

6.  **External Constants/Variables (`extern`):** Extract the names of globally declared constants and variables.
    -   Example: `extern NSString * const MyNotificationName;` -> `MyNotificationName`

7.  **C-style Functions:** Extract the names of C-style function prototypes.
    -   Example: `extern void MyCFunction(int value);` -> `MyCFunction`

## STRICT OUTPUT FORMAT
-   Your output MUST be a single, flat JSON array of strings.
-   The array should contain ONLY the extracted identifier strings.
-   If no public identifiers are found in the file, you MUST output an empty JSON array: `[]`.

## WHAT TO AVOID
-   **ABSOLUTELY NO EXPLANATIONS.** Do not write "Here is the JSON array..." or any other conversational text.
-   **NO MARKDOWN.** Do not wrap the JSON array in ````json` or any other markdown block.
-   **DO NOT EXTRACT COMMENTS.** Ignore anything inside `/* ... */` or after `//`.
-   **DO NOT EXTRACT PARAMETER NAMES.** In `- (void)doSomething:(NSString *)name;`, extract `doSomething:` but NOT `name`.

Analyze the following content and provide ONLY the raw JSON array as your response.

### Header File Content:
```objective-c
{header_content}
```
"""


def process_single_file(header_path: Path, output_path: Path, file_index: int, total_files: int) -> tuple[bool, str]:
    """
    단일 헤더 파일을 처리하는 함수

    Returns:
        tuple[bool, str]: (성공 여부, 결과 메시지)
    """
    try:
        # 이미 처리된 파일인지 확인
        if output_path.exists():
            return True, f"[{file_index}/{total_files}] ⏭️ 건너뜀: {header_path.name} (이미 존재)"

        # 파일 내용 읽기 (여러 인코딩 시도)
        content = None
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'mac-roman']:
            try:
                content = header_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            return False, f"[{file_index}/{total_files}] ❌ 인코딩 오류: {header_path.name} (모든 인코딩 실패)"

        if not content.strip():
            return False, f"[{file_index}/{total_files}] ⚠️ 건너뜀: {header_path.name} (빈 파일)"

        # 프롬프트 구성
        full_prompt = PROMPT_TEMPLATE.format(header_content=content)
        prompt_config = {
            "messages": [
                {"role": "user", "parts": [full_prompt]}
            ]
        }

        # 재시도 로직과 함께 API 호출
        for attempt in range(MAX_RETRIES):
            try:
                response_text = GeminiHandler.ask(prompt_config, model_name=MODEL_NAME)

                # JSON 응답 처리
                clean_response = response_text.strip().removeprefix("```json").removesuffix("```").strip()
                json.loads(clean_response)  # 유효성 검사

                # 파일 저장
                GeminiHandler.save_content(clean_response, str(output_path))
                return True, f"[{file_index}/{total_files}] ✅ 완료: {header_path.name}"

            except json.JSONDecodeError:
                # JSON이 아닌 경우 텍스트로 저장
                GeminiHandler.save_content(response_text, str(output_path.with_suffix(".txt")))
                return False, f"[{file_index}/{total_files}] ⚠️ JSON 오류: {header_path.name} (텍스트로 저장)"

            except (GeminiBlockedError, GeminiResponseEmptyError) as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                    continue
                return False, f"[{file_index}/{total_files}] ❌ API 오류: {header_path.name} - {e}"

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
                    continue
                return False, f"[{file_index}/{total_files}] ❌ 예외: {header_path.name} - {e}"

        return False, f"[{file_index}/{total_files}] ❌ 모든 재시도 실패: {header_path.name}"

    except Exception as e:
        return False, f"[{file_index}/{total_files}] ❌ 파일 처리 오류: {header_path.name} - {e}"


def create_labels_fast():
    """
    배치 처리와 병렬 처리를 사용하여 빠르게 레이블을 생성합니다.
    """
    if not INPUT_DIRECTORY.is_dir():
        print(f"❌ 오류: 입력 디렉토리 '{INPUT_DIRECTORY}'를 찾을 수 없습니다.")
        print("'prepare_headers.py'를 먼저 실행하여 헤더 파일을 준비해주세요.")
        return

    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    print(f"📁 '{OUTPUT_DIRECTORY}' 디렉토리를 확인/생성했습니다.")

    header_files = list(INPUT_DIRECTORY.glob("*.h"))
    total_files = len(header_files)

    if total_files == 0:
        print("❌ 처리할 헤더 파일이 없습니다.")
        return

    print(f"🚀 총 {total_files}개의 헤더 파일을 {MAX_WORKERS}개 스레드로 병렬 처리합니다.")
    print(f"⚙️  배치 크기: {BATCH_SIZE}, 최대 재시도: {MAX_RETRIES}회")

    start_time = time.time()
    success_count = 0
    failed_count = 0

    # 배치 단위로 처리
    for batch_start in range(0, total_files, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_files)
        batch_files = header_files[batch_start:batch_end]

        print(f"\n📦 배치 {batch_start // BATCH_SIZE + 1} 처리 중... ({batch_start + 1}-{batch_end}/{total_files})")

        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 작업 제출
            future_to_file = {}
            for i, header_path in enumerate(batch_files):
                output_path = OUTPUT_DIRECTORY / header_path.with_suffix(".json").name
                file_index = batch_start + i + 1

                future = executor.submit(process_single_file, header_path, output_path, file_index, total_files)
                future_to_file[future] = header_path

                # API 과부하 방지를 위한 딜레이
                time.sleep(REQUEST_DELAY)

            # 결과 처리
            for future in as_completed(future_to_file):
                success, message = future.result()
                print(message)

                if success:
                    success_count += 1
                else:
                    failed_count += 1

        # 배치 간 휴식
        if batch_end < total_files:
            print(f"⏸️  배치 완료. 2초 대기 중...")
            time.sleep(2)

    # 최종 결과 출력
    elapsed_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"🎉 모든 작업이 완료되었습니다!")
    print(f"⏱️  처리 시간: {elapsed_time:.2f}초")
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {failed_count}개")
    print(f"📊 성공률: {success_count / total_files * 100:.1f}%")
    print(f"🚀 평균 처리 속도: {total_files / elapsed_time:.2f}개/초")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    create_labels_fast()