import os
import json
import urllib.request
import urllib.error

try:
    import google.generativeai as genai
except Exception:
    genai = None

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def generate_with_gemini(api_key, prompt):
    if genai is None:
        raise RuntimeError("Biblioteca google-generativeai nao instalada.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
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


def build_prompt(perfil_escritor, temas_ebook, estilo_escrita, autor):
    estilo_final = estilo_escrita or "nao especificado"
    autor_final = autor or "nao informado"
    return f"""

Diretrizes Completas para Geração de eBook em HTML (Formato A4)
🎯 OBJETIVO PRINCIPAL

Gerar o conteúdo integral de um eBook profissional e o respectivo código HTML (apenas o corpo – <body>), totalmente pronto para conversão em PDF no formato A4, com estrutura editorial, narrativa e visual equivalente a um livro digital comercial.

O resultado deve ser um eBook completo, didático, envolvente e bem diagramado.

🧠 CONTEXTO E PAPEL DO ESCRITOR

Atue como um escritor especialista no tema abordado, com domínio técnico e capacidade pedagógica.

A escrita deve ser:

Clara

Fluida

Bem estruturada

Profunda, porém acessível

Envolvente, sem ser prolixa

Use o perfil do escritor informado para ajustar:

Linguagem

Nível técnico

Público-alvo

Tom emocional ou institucional

Forma de escrita preferida: {estilo_final}

O texto deve transmitir autoridade, empatia e clareza.

🖼️ ESTRUTURA INICIAL DO EBOOK
📕 CAPA (Primeira Página)

A capa deve conter:

Título do eBook (centralizado, fonte grande e impactante)

Imagem de fundo relacionada diretamente ao tema do eBook

Visual limpo e profissional

A capa deve ocupar sozinha a primeira página.

📄 PÁGINA DE TÍTULO (Segunda Página)

Deve conter:

Título do eBook em destaque

Subtítulo (se apropriado)

Pequena descrição do propósito do livro

📄 FOLHA DE ROSTO (Terceira Página)

Deve conter:

Nome do autor

Perfil resumido do autor (2–4 linhas)

Ano de publicação

Direitos autorais ou nota editorial simples

📑 ÍNDICE

Deve estar em nova página após a folha de rosto

Deve listar todos os capítulos

Não utilizar numeração de páginas

Deve refletir exatamente a estrutura real dos capítulos

Use layout diferenciado do restante do livro (mais limpo e organizado)

Pode utilizar listas ou blocos estilizados

✨ INTRODUÇÃO

A introdução deve:

Criar conexão emocional ou intelectual com o leitor

Apresentar claramente o problema que o eBook resolve

Explicar por que esse tema é importante

Mostrar o que o leitor vai aprender

Definir expectativas

Pode usar:

Storytelling

Situações reais

Perguntas provocativas

O título principal <h1> e a introdução devem permanecer juntos na primeira página.

📚 ESTRUTURA DOS CAPÍTULOS
Quantidade

Desenvolva entre 5 e 15 capítulos principais, cada um iniciado por <h2>.

Organização interna

Cada capítulo pode conter:

Subtítulos <h3>

Parágrafos explicativos

Listas

Exemplos práticos

Analogias

Mini estudos de caso

Reflexões

Profundidade

Para cada capítulo:

Desenvolva bem as ideias

Evite superficialidade

Construa raciocínio progressivo

Use linguagem clara

Seja didático

Conteúdo enriquecido

Obrigatório:

Criar referências conceituais

Inserir citações (parafraseadas ou diretas) de:

Autores reconhecidos

Livros relevantes

Artigos

Podcasts

Pesquisas

Vídeos

As citações devem ser integradas ao texto, explicando o contexto e conectando com o argumento apresentado.

🧾 CONCLUSÃO (<h2>)

A conclusão deve:

Recapitular os principais aprendizados

Reforçar a mensagem central do livro

Inspirar ação

Pode conter CTA opcional (ex: aplicar o conteúdo, buscar mais conhecimento, etc.)

📐 REGRAS DE FORMATAÇÃO HTML
Estrutura permitida

Utilize exclusivamente:

<h1>
<h2>
<h3>
<p>
<strong>
<ul>
<li>


Não use:

<html>

<head>

<body>

Quebras de página para PDF A4

Imprescindível:

O <h1> e a introdução devem estar na primeira página

Cada novo capítulo (<h2>) deve começar em página nova

A conclusão também deve iniciar em nova página

Para isso:

Insira obrigatoriamente:

<div style="page-break-after: always;"></div>


imediatamente antes de cada <h2>.

🚫 RESTRIÇÕES DE SAÍDA

Gere exclusivamente o HTML do corpo

Não inclua explicações externas

Não escreva frases como “Aqui está o código”

Não inclua comentários técnicos

Não adicione texto fora do eBook

O retorno deve ser apenas o conteúdo final do livro em HTML.

INFORMACOES DO EBOOK:
1. Perfil do escritor:
   {perfil_escritor}
2. Temas principais:
   {temas_ebook}
3. Forma de escrita:
   {estilo_final}
4. Nome do autor:
   {autor_final}

Comece o eBook agora:
"""


@app.route("/gerar-ebook", methods=["POST"])
def gerar_ebook():
    try:
        data = request.get_json(silent=True) or {}
        perfil_escritor = (data.get("perfil") or "").strip()
        temas_ebook = (data.get("temas") or "").strip()
        estilo_escrita = (data.get("estilo") or "").strip()
        autor = (data.get("autor") or "").strip()
        api_provider = (data.get("api_provider") or "gemini").strip().lower()
        api_key = (data.get("api_key") or "").strip()
        openai_model = (data.get("openai_model") or "").strip()

        if not perfil_escritor or not temas_ebook or not autor:
            return jsonify({"error": "Perfil do escritor, nome do autor e temas sao obrigatorios."}), 400

        if not api_key:
            if api_provider == "openai":
                api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
            else:
                api_key = (os.getenv("GEMINI_API_KEY") or "").strip()

        if not api_key:
            return jsonify({"error": "Informe uma API key valida para o provedor selecionado."}), 400

        prompt = build_prompt(perfil_escritor, temas_ebook, estilo_escrita, autor)

        if api_provider == "openai":
            model_name = openai_model or OPENAI_MODEL
            ebook_html = generate_with_openai(api_key, prompt, model_name)
        elif api_provider == "gemini":
            ebook_html = generate_with_gemini(api_key, prompt)
        else:
            return jsonify({"error": "Provedor invalido. Use gemini ou openai."}), 400

        return jsonify({"ebook_html": ebook_html})
    except Exception as e:
        print(f"Erro durante a geracao: {e}")
        return jsonify({"error": f"Ocorreu um erro interno: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
