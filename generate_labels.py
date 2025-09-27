import json
import time
from pathlib import Path
from gemini_handler.gemini_handler import GeminiHandler, GeminiBlockedError, GeminiResponseEmptyError

# --- 설정 ---
# 준비된 헤더 파일이 있는 입력 디렉토리
INPUT_DIRECTORY = Path("./input_headers")

# 생성된 정답 레이블(JSON)을 저장할 출력 디렉토리
OUTPUT_DIRECTORY = Path("./output_labels")

# 사용할 Gemini 모델 이름 (가장 성능이 좋은 모델로 지정)
MODEL_NAME = "gemini-2.5-pro"
# ---

# Gemini API에 전송할 프롬프트 템플릿
# 역할, 목표, 규칙, 출력 형식, 피해야 할 사항을 매우 명확하고 구조적으로 지시합니다.
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


def create_labels():
    """
    input_headers 디렉토리의 각 헤더 파일에 대해 Gemini API를 호출하여
    제외 식별자 목록을 추출하고 JSON 파일로 저장합니다.
    """
    if not INPUT_DIRECTORY.is_dir():
        print(f"오류: 입력 디렉토리 '{INPUT_DIRECTORY}'를 찾을 수 없습니다.")
        print("'prepare_headers.py'를 먼저 실행하여 헤더 파일을 준비해주세요.")
        return

    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    print(f"'{OUTPUT_DIRECTORY}' 디렉토리를 확인/생성했습니다.")

    header_files = list(INPUT_DIRECTORY.glob("*.h"))
    total_files = len(header_files)
    print(f"총 {total_files}개의 헤더 파일을 처리합니다.")

    for i, header_path in enumerate(header_files):
        print(f"\n--- [{i + 1}/{total_files}] 파일 처리 시작: {header_path.name} ---")
        output_path = OUTPUT_DIRECTORY / header_path.with_suffix(".json").name

        if output_path.exists():
            print(f"결과 파일이 이미 존재하여 건너뜁니다: {output_path.name}")
            continue

        try:
            content = header_path.read_text(encoding="utf-8")
            if not content.strip():
                print("파일 내용이 비어있어 건너뜁니다.")
                continue

            # 프롬프트 템플릿에 헤더 파일 내용 삽입
            full_prompt = PROMPT_TEMPLATE.format(header_content=content)

            # GeminiHandler가 요구하는 형식에 맞게 프롬프트 구성
            prompt_config = {
                "messages": [
                    {"role": "user", "parts": [full_prompt]}
                ]
            }

            # Gemini API 호출
            response_text = GeminiHandler.ask(prompt_config, model_name=MODEL_NAME)

            # 응답이 유효한 JSON인지 확인
            try:
                # 불필요한 마크다운 제거 및 JSON 파싱 시도
                clean_response = response_text.strip().removeprefix("```json").removesuffix("```").strip()
                json.loads(clean_response)  # 파싱이 성공하는지만 확인

                # 원본 텍스트를 그대로 저장 (파싱 성공 시)
                GeminiHandler.save_content(clean_response, str(output_path))
                print(f"✅ 성공: 정답 레이블을 '{output_path.name}'에 저장했습니다.")

            except json.JSONDecodeError:
                print(f"⚠️ 경고: API가 유효하지 않은 JSON을 반환했습니다. 원본 텍스트를 저장합니다.")
                # JSON이 아니더라도 나중에 분석할 수 있도록 원본 텍스트를 저장
                GeminiHandler.save_content(response_text, str(output_path.with_suffix(".txt")))


        except (GeminiBlockedError, GeminiResponseEmptyError) as e:
            print(f"❌ 오류: API 응답이 비어있거나 차단되었습니다. ({header_path.name}) - {e}")
        except FileNotFoundError:
            print(f"❌ 오류: 파일을 찾을 수 없습니다. ({header_path.name})")
        except Exception as e:
            print(f"❌ 처리 중 예상치 못한 오류가 발생했습니다. ({header_path.name}) - {e}")

        # API 과부하 방지를 위한 간단한 딜레이
        time.sleep(1)

    print("\n모든 작업이 완료되었습니다.")


if __name__ == "__main__":
    create_labels()

