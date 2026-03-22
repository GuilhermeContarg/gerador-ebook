import os
import json
import urllib.request
import urllib.error
import logging

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")


@app.route("/")
def index():
    return app.send_static_file("index_v2.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def generate_with_gemini(api_key, prompt, model_name="gemini-1.5-flash-latest"):
    if genai is None:
        raise RuntimeError("Biblioteca google-generativeai nao instalada.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text


def generate_with_openai(api_key, prompt, model_name):
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate only the HTML body for the ebook. "
                    "Do not wrap with html/head/body tags."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {error_body}") from exc
    return data["choices"][0]["message"]["content"]


def generate_with_anthropic(api_key, prompt, model_name):
    payload = {
        "model": model_name,
        "max_tokens": 4096,
        "system": "You generate only the HTML body for the ebook. Do not wrap with html/head/body tags.",
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Anthropic HTTP {exc.code}: {error_body}") from exc
    return data["content"][0]["text"]


def build_prompt(perfil_escritor, temas_ebook, estilo_escrita, autor, design_template):
    estilo_final = estilo_escrita or "nao especificado"
    autor_final = autor or "nao informado"
    design_final = design_template or "classico"

    return f"""
Diretrizes Completas para Geração de eBook em HTML (Formato A4)
🎯 OBJETIVO PRINCIPAL

Gerar o conteúdo integral de um eBook profissional e o respectivo código HTML (apenas o corpo – <body>), totalmente pronto para conversão em PDF no formato A4, com estrutura editorial, narrativa e visual equivalente a um livro digital comercial.

O resultado deve ser um eBook completo, didático, envolvente e bem diagramado.

🧠 CONTEXTO E PAPEL DO ESCRITOR
Atue como um escritor especialista no tema abordado, com domínio técnico e capacidade pedagógica.
Forma de escrita preferida: {estilo_final}

O texto deve transmitir autoridade, empatia e clareza.

🖼️ ESTRUTURA INICIAL DO EBOOK
📕 CAPA (Primeira Página)
Deve conter:
- Título do eBook (centralizado, fonte grande e impactante usando as classes CSS do design selecionado: {design_final})
- Uma imagem de fundo ou elemento de destaque visual relacionado diretamente ao tema do eBook (opcional mas recomendado)
A capa deve ocupar sozinha a primeira página.

📄 FOLHA DE ROSTO E METADADOS
Deve conter:
- Nome do autor
- Perfil resumido do autor
- Ano de publicação
- Injeção de metadados: gere uma div invisível com os metadados do ebook (<div class="metadata" style="display:none;" data-author="{autor_final}" data-style="{estilo_final}"></div>).

📑 SUMÁRIO (ÍNDICE) DINÂMICO
A IA DEVE GERAR um sumário completo de todos os capítulos usando links internos (<a href="#capitulo-X">).
Cada título de capítulo deverá ter um id correspondente (<h2 id="capitulo-X">).

✨ INTRODUÇÃO E CAPÍTULOS
Desenvolva entre 5 e 15 capítulos principais.
Use <h2> com o atributo id correspondente ao sumário.
Crie conteúdo aprofundado, com referências conceituais e citações integradas ao texto.

🧾 CONCLUSÃO
Recapitulando os principais aprendizados e inspirando a ação.

📐 REGRAS DE FORMATAÇÃO HTML
Não use: <html>, <head>, <body>.
Apenas tags limpas e semânticas.
Insira obrigatoriamente: <div style="page-break-after: always;"></div> imediatamente antes de cada <h2> para forçar quebra de página em PDF.

INFORMACOES DO EBOOK:
1. Perfil do escritor: {perfil_escritor}
2. Temas principais: {temas_ebook}
3. Forma de escrita: {estilo_final}
4. Nome do autor: {autor_final}
5. Tema de Design: {design_final}

Gere apenas o HTML resultante, focado no conteúdo robusto e bem formatado.
"""


@app.route("/gerar-ebook", methods=["POST"])
def gerar_ebook():
    try:
        data = request.get_json(silent=True) or {}
        perfil_escritor = (data.get("perfil") or "").strip()
        temas_ebook = (data.get("temas") or "").strip()
        estilo_escrita = (data.get("estilo") or "").strip()
        autor = (data.get("autor") or "").strip()
        design_template = (data.get("design") or "classico").strip()

        api_provider = (data.get("api_provider") or "gemini").strip().lower()
        api_key = (data.get("api_key") or "").strip()

        # Recupera chaves do ambiente caso não sejam enviadas pela UI (Segurança)
        if not api_key:
            if api_provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY", "").strip()
            elif api_provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            else:
                api_key = os.getenv("GEMINI_API_KEY", "").strip()

        if not perfil_escritor or not temas_ebook or not autor:
            return jsonify({"error": "Perfil do escritor, nome do autor e temas sao obrigatorios."}), 400

        if not api_key:
            return jsonify({"error": f"Chave de API nao encontrada para o provedor {api_provider}."}), 400

        prompt = build_prompt(perfil_escritor, temas_ebook, estilo_escrita, autor, design_template)

        logger.info(f"Gerando eBook usando provedor: {api_provider}")

        if api_provider == "openai":
            model_name = data.get("openai_model") or OPENAI_MODEL
            ebook_html = generate_with_openai(api_key, prompt, model_name)
        elif api_provider == "anthropic":
            model_name = data.get("anthropic_model") or ANTHROPIC_MODEL
            ebook_html = generate_with_anthropic(api_key, prompt, model_name)
        elif api_provider == "gemini":
            model_name = data.get("gemini_model") or GEMINI_MODEL
            ebook_html = generate_with_gemini(api_key, prompt, model_name)
        else:
            return jsonify({"error": "Provedor invalido. Use gemini, openai ou anthropic."}), 400

        return jsonify({"ebook_html": ebook_html})
    except Exception as e:
        logger.error(f"Erro durante a geracao: {e}", exc_info=True)
        return jsonify({"error": f"Ocorreu um erro interno: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
