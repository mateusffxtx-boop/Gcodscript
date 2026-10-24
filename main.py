
import flet as ft
import requests
import json
import os
from pathlib import Path

APP_DIR = Path.home() / ".gcodscript_ai"
APP_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = APP_DIR / "settings.json"
HISTORY_FILE = APP_DIR / "history.json"

# Modelos de texto disponíveis na API Gemini.
GEMINI_MODELS = {
    "Gemini 3.8 Flash — recomendado": "gemini-3.8-flash",
    "Gemini 3.6 Flash": "gemini-3.6-flash",
    "Gemini 3.5 Flash-Lite — econômico": "gemini-3.5-flash-lite",
    "Gemini 3.1 Flash-Lite": "gemini-3.1-flash-lite",
    "Gemini 3 Flash — prévia": "gemini-3-flash-preview",
    "Gemini 3.1 Pro — prévia": "gemini-3.1-pro-preview",
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Flash-Lite": "gemini-2.5-flash-lite",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
}

DEFAULT_SETTINGS = {
    "api_key": "",
    "model": "gemini-3.8-flash",
    "mode": "Online",
    "local_url": "http://127.0.0.1:8080/v1/chat/completions",
    "local_model": "local-model",
}


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default.copy() if isinstance(default, dict) else default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
history = load_json(HISTORY_FILE, [])

if not isinstance(history, list):
    history = []

if settings.get("model") not in GEMINI_MODELS.values():
    settings["model"] = "gemini-3.8-flash"


def main(page: ft.Page):
    page.title = "Gcodscript AI"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#10131A"
    page.padding = 12

    if not history:
        history.append({
            "title": "Nova conversa",
            "messages": []
        })

    current_chat = len(history) - 1

    api_key = ft.TextField(
        label="Chave da API Gemini",
        value=settings.get("api_key", ""),
        password=True,
        can_reveal_password=True,
    )

    model_dropdown = ft.Dropdown(
        label="Modelo Gemini",
        value=settings.get("model", "gemini-3.8-flash"),
        options=[
            ft.dropdown.Option(key=model_id, text=label)
            for label, model_id in GEMINI_MODELS.items()
        ],
    )

    mode = ft.Dropdown(
        label="Modo de funcionamento",
        value=settings.get("mode", "Online"),
        options=[
            ft.dropdown.Option("Online"),
            ft.dropdown.Option("Local"),
        ],
    )

    local_url = ft.TextField(
        label="URL do servidor local",
        value=settings.get("local_url", ""),
    )

    local_model = ft.TextField(
        label="Nome do modelo local",
        value=settings.get("local_model", "local-model"),
    )

    prompt_field = ft.TextField(
        hint_text="Digite sua mensagem...",
        multiline=True,
        min_lines=1,
        max_lines=5,
        expand=True,
    )

    chat_column = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=10,
    )

    status = ft.Text("Pronto", color="#9AA4B2")

    def persist():
        save_json(SETTINGS_FILE, settings)
        save_json(HISTORY_FILE, history)

    def add_message(role, content):
        is_ai = role == "assistant"
        label = "Gcodscript AI" if is_ai else "Você"
        color = "#202633" if is_ai else "#253B56"

        chat_column.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(label, weight=ft.FontWeight.BOLD),
                        ft.Text(content, selectable=True),
                    ],
                    spacing=5,
                ),
                bgcolor=color,
                padding=12,
                border_radius=12,
            )
        )
        page.update()

    def redraw_chat():
        chat_column.controls.clear()

        for message in history[current_chat]["messages"]:
            add_message(message["role"], message["content"])

        page.update()

    def new_chat(e=None):
        nonlocal current_chat

        history.append({
            "title": "Nova conversa",
            "messages": []
        })

        current_chat = len(history) - 1
        persist()
        redraw_chat()

        status.value = "Nova conversa criada"
        page.update()

    def clear_chat(e=None):
        history[current_chat]["messages"] = []
        history[current_chat]["title"] = "Nova conversa"

        persist()
        redraw_chat()

        status.value = "Conversa apagada"
        page.update()

    def save_settings(e=None):
        settings["api_key"] = (api_key.value or "").strip()
        settings["model"] = (
            model_dropdown.value or "gemini-3.8-flash"
        )
        settings["mode"] = mode.value or "Online"
        settings["local_url"] = (local_url.value or "").strip()
        settings["local_model"] = (
            (local_model.value or "").strip() or "local-model"
        )

        persist()
        status.value = "Configurações salvas"
        page.update()

    def ask_ai(e=None):
        prompt = (prompt_field.value or "").strip()

        if not prompt:
            return

        prompt_field.value = ""

        history[current_chat]["messages"].append({
            "role": "user",
            "content": prompt
        })

        add_message("user", prompt)

        if history[current_chat]["title"] == "Nova conversa":
            history[current_chat]["title"] = prompt[:35]

        status.value = "A IA está respondendo..."
        send_button.disabled = True
        page.update()

        try:
            if settings.get("mode") == "Local":
                # Requer um servidor local compatível com a API OpenAI.
                response = requests.post(
                    settings["local_url"],
                    json={
                        "model": settings["local_model"],
                        "messages": history[current_chat]["messages"],
                        "temperature": 0.7,
                    },
                    timeout=180,
                )

                response.raise_for_status()
                data = response.json()
                answer = data["choices"][0]["message"]["content"]

            else:
                key = settings.get("api_key", "").strip()
                model_name = settings.get(
                    "model", "gemini-3.8-flash"
                )

                if not key:
                    raise ValueError(
                        "Adicione sua chave da API Gemini nas configurações."
                    )

                url = (
                    "https://generativelanguage.googleapis.com/"
                    f"v1beta/models/{model_name}:generateContent"
                )

                contents = []

                for message in history[current_chat]["messages"]:
                    role = (
                        "user"
                        if message["role"] == "user"
                        else "model"
                    )

                    contents.append({
                        "role": role,
                        "parts": [{"text": message["content"]}]
                    })

                response = requests.post(
                    url,
                    params={"key": key},
                    json={
                        "contents": contents,
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 8192,
                        },
                    },
                    timeout=120,
                )

                if not response.ok:
                    try:
                        details = response.json().get("error", {}).get(
                            "message", response.text
                        )
                    except ValueError:
                        details = response.text

                    raise RuntimeError(
                        f"API Gemini ({response.status_code}): {details}"
                    )

                data = response.json()
                candidates = data.get("candidates", [])

                if not candidates:
                    raise RuntimeError(
                        "A API não retornou uma resposta. "
                        "Verifique o acesso ao modelo."
                    )

                parts = candidates[0].get("content", {}).get("parts", [])
                answer = "\n".join(
                    part["text"]
                    for part in parts
                    if "text" in part
                )

                if not answer:
                    answer = "A API retornou uma resposta vazia."

        except Exception as error:
            answer = f"Erro: {error}"

        history[current_chat]["messages"].append({
            "role": "assistant",
            "content": answer
        })

        add_message("assistant", answer)
        persist()

        status.value = "Pronto"
        send_button.disabled = False
        page.update()

    send_button = ft.IconButton(
        icon=ft.Icons.SEND,
        tooltip="Enviar mensagem",
        on_click=ask_ai,
    )

    chat_view = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Gcodscript AI",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.ADD,
                        tooltip="Nova conversa",
                        on_click=new_chat,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip="Limpar conversa",
                        on_click=clear_chat,
                    ),
                ]
            ),
            ft.Divider(),
            chat_column,
            ft.Row([prompt_field, send_button]),
            status,
        ],
        expand=True,
    )

    filename_field = ft.TextField(
        label="Nome do arquivo",
        value="script.py",
    )

    canvas_text = ft.TextField(
        label="Editor de código",
        multiline=True,
        min_lines=15,
        max_lines=30,
        expand=True,
        text_size=13,
    )

    def save_code(e=None):
        name = os.path.basename(
            (filename_field.value or "script.py").strip()
        ) or "script.py"

        destination = APP_DIR / name
        destination.write_text(
            canvas_text.value or "",
            encoding="utf-8",
        )

        status.value = f"Arquivo salvo em: {destination}"
        page.update()

    def analyze_code(e=None):
        code = canvas_text.value or ""

        if not code.strip():
            status.value = "Digite ou cole um código primeiro."
            page.update()
            return

        prompt_field.value = (
            "Analise este código, encontre erros e sugira melhorias:\n\n"
            + code
        )

        page.go("/chat")

    canvas_view = ft.Column(
        [
            ft.Text(
                "Canvas de código",
                size=22,
                weight=ft.FontWeight.BOLD,
            ),
            filename_field,
            canvas_text,
            ft.Row(
                [
                    ft.ElevatedButton(
                        "Salvar arquivo",
                        icon=ft.Icons.SAVE,
                        on_click=save_code,
                    ),
                    ft.ElevatedButton(
                        "Analisar com IA",
                        icon=ft.Icons.CODE,
                        on_click=analyze_code,
                    ),
                ],
                wrap=True,
            ),
        ],
        expand=True,
    )

    settings_view = ft.Column(
        [
            ft.Text(
                "Configurações",
                size=22,
                weight=ft.FontWeight.BOLD,
            ),
            api_key,
            model_dropdown,
            ft.Text(
                "Escolha um modelo de texto. "
                "Alguns modelos podem exigir acesso específico."
            ),
            mode,
            local_url,
            local_model,
            ft.Text(
                "O modo Local exige um servidor de IA local ativo. "
                "Ele não instala nem baixa modelos automaticamente."
            ),
            ft.ElevatedButton(
                "Salvar configurações",
                icon=ft.Icons.SAVE,
                on_click=save_settings,
            ),
            ft.Text(
                f"Pasta de dados: {APP_DIR}",
                selectable=True,
                size=12,
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    def route_change(e):
        page.views.clear()
        route = page.route or "/chat"

        if route == "/canvas":
            content = canvas_view
        elif route == "/settings":
            content = settings_view
        else:
            content = chat_view

        page.views.append(
            ft.View(
                route=route,
                controls=[
                    content,
                    ft.Row(
                        [
                            ft.TextButton(
                                "Chat",
                                icon=ft.Icons.CHAT,
                                on_click=lambda _: page.go("/chat"),
                            ),
                            ft.TextButton(
                                "Canvas",
                                icon=ft.Icons.CODE,
                                on_click=lambda _: page.go("/canvas"),
                            ),
                            ft.TextButton(
                                "Config",
                                icon=ft.Icons.SETTINGS,
                                on_click=lambda _: page.go("/settings"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    ),
                ],
                padding=12,
            )
        )

        page.update()

    page.on_route_change = route_change
    page.go("/chat")
    redraw_chat()


ft.app(target=main)
