import flet as ft
import json
import os
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

# =========================
# CONFIGURAÇÃO DO APLICATIVO
# =========================


def get_app_dir():
    """Escolhe uma pasta onde o app realmente consegue gravar."""
    candidates = []

    # Pasta de dados própria do app (Android/iOS), definida pelo Flet
    storage = os.getenv("FLET_APP_STORAGE_DATA")
    if storage:
        candidates.append(Path(storage) / "gcodscript_ai")

    # Desktop / testes no computador
    candidates.append(Path.home() / ".gcodscript_ai")

    # Último recurso: pasta temporária
    candidates.append(Path(tempfile.gettempdir()) / "gcodscript_ai")

    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            return folder
        except OSError:
            continue

    return Path(tempfile.gettempdir())


APP_DIR = get_app_dir()

SETTINGS_FILE = APP_DIR / "settings.json"
HISTORY_FILE = APP_DIR / "history.json"

GEMINI_MODELS = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Flash-Lite": "gemini-2.5-flash-lite",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 3 Flash Preview": "gemini-3-flash-preview",
    "Gemini 3.1 Pro Preview": "gemini-3.1-pro-preview",
}

DEFAULT_SETTINGS = {
    "api_key": "",
    "model": "gemini-2.5-flash",
    "mode": "Online",
    "local_url": "http://127.0.0.1:8080/v1/chat/completions",
    "local_model": "local-model",
}

# Compatível com versões diferentes do Flet
DropdownOption = getattr(ft, "DropdownOption", None)
if DropdownOption is None:
    DropdownOption = ft.dropdown.Option


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return default.copy() if isinstance(default, dict) else default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except OSError:
        # Se não for possível gravar, o app continua funcionando
        pass


settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
history = load_json(HISTORY_FILE, [])

if not isinstance(settings, dict):
    settings = DEFAULT_SETTINGS.copy()

if not isinstance(history, list):
    history = []

if settings.get("model") not in GEMINI_MODELS.values():
    settings["model"] = "gemini-2.5-flash"


# =========================
# REQUISIÇÕES SEM REQUESTS
# =========================

def http_post(url, payload, headers=None, timeout=120):
    body = json.dumps(payload).encode("utf-8")

    request_headers = {
        "Content-Type": "application/json",
    }

    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Erro HTTP {error.code}: {details[:1500]}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Não foi possível conectar: {error.reason}"
        ) from error


# =========================
# APLICATIVO
# =========================

def main(page: ft.Page):
    page.title = "Gcodscript AI"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#10131A"
    page.padding = 12

    if not history:
        history.append({
            "title": "Nova conversa",
            "messages": [],
        })

    current_chat = len(history) - 1

    # ---------- Campos de configuração ----------

    api_key = ft.TextField(
        label="Chave da API Gemini",
        value=settings.get("api_key", ""),
        password=True,
        can_reveal_password=True,
    )

    model_dropdown = ft.Dropdown(
        label="Modelo Gemini",
        value=settings.get("model", "gemini-2.5-flash"),
        options=[
            DropdownOption(key=model_id, text=label)
            for label, model_id in GEMINI_MODELS.items()
        ],
    )

    mode_dropdown = ft.Dropdown(
        label="Modo de funcionamento",
        value=settings.get("mode", "Online"),
        options=[
            DropdownOption(key="Online", text="Online"),
            DropdownOption(key="Local", text="Local"),
        ],
    )

    local_url = ft.TextField(
        label="URL do servidor local",
        value=settings.get("local_url", DEFAULT_SETTINGS["local_url"]),
    )

    local_model = ft.TextField(
        label="Nome do modelo local",
        value=settings.get("local_model", "local-model"),
    )

    # ---------- Chat ----------

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

        chat_column.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Gcodscript AI" if is_ai else "Você",
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(content, selectable=True),
                    ],
                    spacing=5,
                ),
                bgcolor="#202633" if is_ai else "#253B56",
                padding=12,
                border_radius=12,
            )
        )

    def redraw_chat():
        chat_column.controls.clear()

        for message in history[current_chat]["messages"]:
            add_message(message["role"], message["content"])

        page.update()

    def new_chat(e=None):
        nonlocal current_chat

        history.append({
            "title": "Nova conversa",
            "messages": [],
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
        settings["model"] = model_dropdown.value or "gemini-2.5-flash"
        settings["mode"] = mode_dropdown.value or "Online"
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
            "content": prompt,
        })

        if history[current_chat]["title"] == "Nova conversa":
            history[current_chat]["title"] = prompt[:35]

        add_message("user", prompt)

        status.value = "A IA está respondendo..."
        send_button.disabled = True
        page.update()

        try:
            if settings.get("mode") == "Local":
                # Precisa de um servidor local compatível com a API da OpenAI.
                result = http_post(
                    settings["local_url"],
                    {
                        "model": settings["local_model"],
                        "messages": history[current_chat]["messages"],
                        "temperature": 0.7,
                    },
                    timeout=180,
                )

                answer = result["choices"][0]["message"]["content"]

            else:
                key = settings.get("api_key", "").strip()

                if not key:
                    raise ValueError(
                        "Abra Config e informe sua chave da API Gemini."
                    )

                model_name = settings.get("model", "gemini-2.5-flash")

                url = (
                    "https://generativelanguage.googleapis.com/"
                    f"v1beta/models/{model_name}:generateContent"
                    f"?key={key}"
                )

                contents = []

                for message in history[current_chat]["messages"]:
                    role = "user" if message["role"] == "user" else "model"

                    contents.append({
                        "role": role,
                        "parts": [{"text": message["content"]}],
                    })

                result = http_post(
                    url,
                    {
                        "contents": contents,
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 8192,
                        },
                    },
                    timeout=120,
                )

                candidates = result.get("candidates", [])

                if not candidates:
                    raise RuntimeError(
                        "A API não retornou resposta. "
                        "Verifique o modelo e as permissões da sua chave."
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
            "content": answer,
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

    # =========================
    # CANVAS DE CÓDIGO
    # =========================

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

        try:
            destination.write_text(
                canvas_text.value or "",
                encoding="utf-8",
            )
            status.value = f"Arquivo salvo em: {destination}"
        except OSError as error:
            status.value = f"Não foi possível salvar: {error}"

        page.update()

    def analyze_code(e=None):
        code = canvas_text.value or ""

        if not code.strip():
            status.value = "Digite ou cole algum código primeiro."
            page.update()
            return

        prompt_field.value = (
            "Analise este código, identifique erros e sugira melhorias:\n\n"
            + code
        )

        show_view("chat")

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

    # =========================
    # CONFIGURAÇÕES
    # =========================

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
                "A disponibilidade dos modelos depende da API Gemini "
                "e das permissões da sua chave."
            ),
            mode_dropdown,
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

    # =========================
    # NAVEGAÇÃO ENTRE TELAS
    # =========================

    body = ft.Container(content=chat_view, expand=True)

    def show_view(name):
        if name == "canvas":
            body.content = canvas_view
        elif name == "settings":
            body.content = settings_view
        else:
            body.content = chat_view

        page.update()

    nav_row = ft.Row(
        [
            ft.TextButton(
                "Chat",
                icon=ft.Icons.CHAT,
                on_click=lambda _: show_view("chat"),
            ),
            ft.TextButton(
                "Canvas",
                icon=ft.Icons.CODE,
                on_click=lambda _: show_view("canvas"),
            ),
            ft.TextButton(
                "Config",
                icon=ft.Icons.SETTINGS,
                on_click=lambda _: show_view("settings"),
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_AROUND,
    )

    page.add(body, nav_row)
    redraw_chat()


if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
