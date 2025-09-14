import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions
from google.generativeai.types import HarmCategory, HarmBlockThreshold


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
dotenv_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=dotenv_path)
sys.path.append(str(SCRIPT_DIR))
API_KEY_NAMES = [
    "GEMINI_API_KEY_KS", "GEMINI_API_KEY_DH", "GEMINI_API_KEY_GN", "GEMINI_API_KEY_HJ",
    "GEMINI_API_KEY_SH", "GEMINI_API_KEY_SI", "GEMINI_API_KEY_BW", "GEMINI_API_KEY_SW",
]
API_KEYS = [os.getenv(key_name) for key_name in API_KEY_NAMES if os.getenv(key_name)]
if not API_KEYS:
    raise ValueError("하나 이상의 GEMINI_API_KEY가 .env 파일에 설정되어야 합니다.")


class GeminiResponseEmptyError(RuntimeError): pass


class GeminiBlockedError(RuntimeError): pass


# ---

class GeminiHandler:
    api_keys = API_KEYS
    current_key_index = 0

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    generation_config = {
        "temperature": 0.2,
        "max_output_tokens": 65536,
    }

    # /// 모델 이름을 파라미터로 받아 유연성을 높임
    @classmethod
    def _get_configured_model(cls, model_name: str, system_instruction: str | None = None):
        if cls.current_key_index >= len(cls.api_keys):
            raise RuntimeError("사용 가능한 모든 Gemini API 키가 소진되었습니다.")

        current_key = cls.api_keys[cls.current_key_index]
        genai.configure(api_key=current_key)

        return genai.GenerativeModel(
            model_name=model_name,
            safety_settings=cls.safety_settings,
            generation_config=cls.generation_config,
            system_instruction=system_instruction
        )

    @classmethod
    def ask(cls, prompt_config: dict, model_name: str, retries: int = 3, base_wait: int = 5) -> str:
        messages = prompt_config.get("messages")
        if not messages:
            raise ValueError("프롬프트 설정에 'messages' 키가 없거나 비어있습니다.")

        # 시스템 프롬프트와 사용자 메시지를 명확하게 분리.
        system_prompt_parts = []
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt_parts.extend(msg.get("parts", []))
            else:
                user_messages.append(msg)

        system_prompt = "\n".join(system_prompt_parts) if system_prompt_parts else None

        last_err = None
        for attempt in range(1, retries + 1):
            try:
                print(f"🔑 Gemini API 키 #{cls.current_key_index + 1}로 [{model_name}] 모델에 요청 시도...")
                # model_name과 분리된 system_prompt를 전달.
                model = cls._get_configured_model(model_name=model_name, system_instruction=system_prompt)

                # user_messages만 generate_content에 전달.
                resp = model.generate_content(
                    user_messages,
                    request_options={"timeout": 300}
                )

                if not resp.candidates:
                    block_reason = "Unknown"
                    if hasattr(resp, 'prompt_feedback') and resp.prompt_feedback.block_reason:
                        block_reason = resp.prompt_feedback.block_reason.name
                    raise GeminiBlockedError(f"응답이 차단됨 (No candidates returned). Block Reason: {block_reason}")

                candidate = resp.candidates[0]
                if not candidate.content or not candidate.content.parts:
                    raise GeminiBlockedError(f"콘텐츠가 없음 (finish_reason={candidate.finish_reason.name})")

                text = candidate.content.parts[0].text
                if not text or not text.strip():
                    raise GeminiResponseEmptyError(f"빈 텍스트 응답 (finish_reason={candidate.finish_reason.name})")

                return text.strip()

            except exceptions.ResourceExhausted as e:
                # === MODIFIED SECTION START ===
                # 사용량 한도 초과 시, 키를 바꾸는 대신 61초간 대기하여 한도가 초기화되기를 기다립니다.
                wait_time = 300
                print(f"  ⚠️ Gemini API 키 #{cls.current_key_index + 1}의 사용량 한도 도달. {wait_time}초 후 같은 키로 재시도합니다... ({attempt}/{retries})")
                time.sleep(wait_time)
                last_err = e
                # 다음 재시도를 위해 루프의 다음 단계로 넘어갑니다.
                continue
                # === MODIFIED SECTION END ===

            except (GeminiResponseEmptyError, GeminiBlockedError) as e:
                wait = base_wait * (2 ** (attempt - 1))
                print(f"  ⚠️ 비어 있거나 차단된 응답. {wait}초 후 재시도... ({attempt}/{retries}) :: {e}")
                time.sleep(wait)
                last_err = e

            except exceptions.DeadlineExceeded as e:
                wait = base_wait * (2 ** (attempt - 1))
                print(f"  ⚠️ API 요청 시간 초과. {wait}초 후 재시도... ({attempt}/{retries})")
                time.sleep(wait)
                last_err = e

            except Exception as e:
                wait = base_wait * (2 ** (attempt - 1))
                error_summary = str(e).split('\n')[0]
                print(f"  ⚠️ 예상치 못한 오류. {wait}초 후 재시도... ({attempt}/{retries}) :: {error_summary}")
                time.sleep(wait)
                last_err = e

        raise RuntimeError(f"Gemini가 {retries}번의 재시도 후 실패했습니다: {last_err}")

    @staticmethod
    def save_content(content: str, output_path: str):
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)
