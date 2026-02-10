import os
import queue
import threading
from dataclasses import dataclass

import pyttsx3
import speech_recognition as sr
from openai import OpenAI


@dataclass
class AssistantConfig:
    wake_words: tuple[str, ...] = ("ассистент", "assistant", "чат gpt", "chatgpt")
    model: str = "gpt-4o-mini"
    language: str = "ru-RU"
    timeout_seconds: int = 5
    phrase_time_limit: int = 8


class VoiceAssistant:
    def __init__(self, config: AssistantConfig) -> None:
        self.config = config
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.recognizer = sr.Recognizer()
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", 170)
        self.messages: queue.Queue[str] = queue.Queue()
        self.running = True

    def _speak(self, text: str) -> None:
        print(f"[ASSISTANT] {text}")
        self.tts.say(text)
        self.tts.runAndWait()

    def _contains_wake_word(self, text: str) -> bool:
        lowered = text.lower().strip()
        return any(w in lowered for w in self.config.wake_words)

    def _strip_wake_word(self, text: str) -> str:
        lowered = text.lower()
        for word in self.config.wake_words:
            lowered = lowered.replace(word, "").strip(" ,.!?:;-")
        return lowered.strip()

    def _listen_worker(self) -> None:
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Слушаю в фоне... Скажи wake-word и запрос.")
            while self.running:
                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.config.timeout_seconds,
                        phrase_time_limit=self.config.phrase_time_limit,
                    )
                    text = self.recognizer.recognize_google(
                        audio, language=self.config.language
                    )
                    print(f"[YOU] {text}")
                    if self._contains_wake_word(text):
                        request = self._strip_wake_word(text)
                        if request:
                            self.messages.put(request)
                        else:
                            self._speak("Я слушаю. Сформулируй запрос после обращения.")
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as exc:
                    print(f"Ошибка распознавания: {exc}")

    def _ask_gpt(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.config.model,
            input=prompt,
        )
        answer = response.output_text.strip()
        return answer or "Я не смог сформировать ответ."

    def run(self) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Не задан OPENAI_API_KEY.")

        self._speak("Голосовой ассистент запущен и работает в фоне.")

        listener = threading.Thread(target=self._listen_worker, daemon=True)
        listener.start()

        try:
            while True:
                prompt = self.messages.get()
                print(f"[PROMPT] {prompt}")
                try:
                    answer = self._ask_gpt(prompt)
                except Exception as exc:
                    answer = f"Ошибка при обращении к ChatGPT: {exc}"
                self._speak(answer)
        except KeyboardInterrupt:
            self.running = False
            self._speak("Останавливаюсь. Пока!")


def print_usage() -> None:
    print("""
Запуск:
  OPENAI_API_KEY=ваш_ключ python main.py

Как пользоваться:
  1) Оставь программу запущенной в фоне.
  2) Обращайся с wake-word: ассистент / assistant / chatgpt.
  3) Пример: "ассистент какая сегодня погода".
""".strip())


if __name__ == "__main__":
    print_usage()
    assistant = VoiceAssistant(AssistantConfig())
    assistant.run()
