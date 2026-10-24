
import asyncio
import json
import urllib.error
import urllib.request

import flet as ft

MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "Você é um assistente útil, claro e cuidadoso. "
    "Responda em português do Brasil por padrão. "
    "Se não souber algo, diga isso com honestidade."
)


def main(page: ft.Page):
    page.title = "Gcodscript AI"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#10131A"
    page.padding = 0

    history = []
    busy = False

    api_key = ft.TextField(
        label="Chave da Gemini API",
        hint_text="Cole sua chave aqui",
        password=True,
        can_reveal_password=True,
        border_radius=12,
        dense=True,
        expand=True,
    )

    status = ft.Text(
        "A chave não é salva pelo aplicativo. Ela fica na sessão atual.",
        size=12,
        color="#AAB3C5",
    )

    chat = ft.ListView(
        expand=True,
        spacing=12,
        auto_scroll=True,
        padding=16,
    )

    prompt = ft.TextField(
        hint_text="Escreva sua mensagem…",
        multiline=True,
        min_lines=1,
        max_lines=4,
        border_radius=18,
        expand=True,
    )

    send_button = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        icon_color="#FFFFFF",
        bgcolor="#5865F2",
        tooltip="Enviar mensagem",
    )

    def add_bubble(message, from_user=False):
        bubble = ft.Container(
            content=ft.Text(
                message,
                selectable=True,
                color="#FFFFFF",
                size=15,
            ),
            bgcolor="#5865F2" if from_user else "#222836",
            border_radius=16,
            padding=14,
            width=page.width * 0.86 if page.width else 420,
        )

        chat.controls.append(
            ft.Row(
                [bubble],
                alignment=(
                    ft.MainAxisAlignment.END
                    if from_user
                    else ft.MainAxisAlignment.START
                ),
            )
        )
        page.update()

    def call_gemini(key, contents):
        body = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + MODEL
            + ":generateContent"
        )

        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))

            return "".join(
                part.get("text", "")
                for part in data["candidates"][0]["content"]["parts"]
                if "text" in part
            ).strip() or "A resposta veio vazia. Tente novamente."

        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
                message = detail.get("error", {}).get(
                    "message", "Erro da API."
                )
            except Exception:
                message = "A API recusou a solicitação."

            raise RuntimeError(
                f"Erro Gemini ({exc.code}): {message}"
            ) from None

        except urllib.error.URLError:
            raise RuntimeError(
                "Sem conexão com a internet. Confira sua rede."
            ) from None

        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise RuntimeError(
                "A resposta da Gemini veio em um formato inesperado."
            ) from None

    async def send_message(e=None):
        nonlocal busy

        message = (prompt.value or "").strip()
        key = (api_key.value or "").strip()

        if busy:
            return

        if not key:
            status.value = (
                "Cole sua chave da Gemini API antes de enviar."
            )
            status.color = "#FFB86B"
            page.update()
            return

        if not message:
            return

        busy = True
        prompt.value = ""
        prompt.disabled = True
        send_button.disabled = True

        status.value = "Pensando…"
        status.color = "#AAB3C5"

        add_bubble(message, from_user=True)

        contents = list(history)
        contents.append(
            {
                "role": "user",
                "parts": [{"text": message}],
            }
        )

        page.update()

        try:
            answer = await asyncio.to_thread(
                call_gemini,
                key,
                contents,
            )

            history.append(
                {
                    "role": "user",
                    "parts": [{"text": message}],
                }
            )

            history.append(
                {
                    "role": "model",
                    "parts": [{"text": answer}],
                }
            )

            add_bubble(answer)

            status.value = f"Conectado • {MODEL}"
            status.color = "#8DD9A8"

        except Exception as exc:
            status.value = str(exc)
            status.color = "#FF8C8C"
            add_bubble(f"Não consegui responder.\n{exc}")

        finally:
            busy = False
            prompt.disabled = False
            send_button.disabled = False
            page.update()

    def clear_chat(e):
        history.clear()
        chat.controls.clear()

        status.value = "Conversa limpa."
        status.color = "#AAB3C5"

        page.update()

    send_button.on_click = send_message
    prompt.on_submit = send_message

    header = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.AUTO_AWESOME,
                        color="#FFFFFF",
                        size=26,
                    ),
                    bgcolor="#5865F2",
                    padding=12,
                    border_radius=14,
                ),
                ft.Column(
                    [
                        ft.Text(
                            "Gcodscript AI",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "Assistente com Gemini",
                            size=13,
                            color="#AAB3C5",
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Limpar conversa",
                    on_click=clear_chat,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=16,
        bgcolor="#171B25",
    )

    setup = ft.Container(
        content=ft.Column(
            [api_key, status],
            spacing=6,
        ),
        # Corrigido: removido ft.padding.symmetric incompatível.
        padding=10,
    )

    composer = ft.Container(
        content=ft.Row(
            [prompt, send_button],
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
        padding=12,
        bgcolor="#171B25",
    )

    page.add(
        ft.Column(
            [
                header,
                setup,
                ft.Divider(height=1, color="#2A3040"),
                chat,
                composer,
            ],
            expand=True,
            spacing=0,
        )
    )

    add_bubble(
        "Olá! 👋\n"
        "Cole sua chave da Gemini API acima e envie uma mensagem "
        "para começar."
    )


if __name__ == "__main__":
    ft.run(main)
