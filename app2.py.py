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

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
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

### Objetivo principal
Gerar o conteudo completo e o codigo HTML (apenas *body*) para um eBook sobre o tema solicitado,
pronto para conversao em PDF no formato A4.

### Contexto e papel
Atue como escritor especialista e web designer senior. A escrita deve ser envolvente, clara e estruturada.
Use o perfil do escritor abaixo para ajustar publico e tom.
Forma de escrita preferida: {estilo_final}.

### Instrucoes especificas
- Titulo principal em <h1>, atraente e claro.
- CAPA:
  - Deve conter o titulo do eBook.
  - Deve ter uma imagem de fundo relacionada ao tema do eBook.
  - O titulo deve estar centralizado na capa, com fonte grande e legivel.
  - O nome do autor deve estar na parte inferior de uma pagina posterior a capa.
- Deve haver pagina do titulo e, na pagina seguinte, a folha de rosto com as informacoes do autor.
- INDICE:
  - Deve listar todos os capitulos sem numeros de pagina.
  - Deve ser gerado com base na estrutura dos capitulos.
  - Deve estar em uma nova pagina apos a folha de rosto.
  - Use um layout diferente do restante do eBook, mas ainda profissional.
- Introducao:
  - Envolvente, usando storytelling ou apresentando o problema que o eBook resolve.
  - Apresente o objetivo do eBook e um resumo do que sera abordado.
- Estrutura de capitulos:
  - Desenvolva de 5 a 15 capitulos principais (<h2>).
  - Cada capitulo pode ter subtitulos (<h3>) e paragrafos detalhados.
  - Use listas quando apropriado, exemplos praticos, estudos de caso ou analogias. 
  - seja detalhista e claro, sem perder o foco. trabalhe bem as ideias e as informaÇõÇæes.
  - Crie referencias e citaÇõÇæes para respaudar 
  - pesquise escritores que falaram ou sÇœo referencias no assunto do eBook.para criar as citaÇõÇæes. e trabalhar as ideias
  - pesquise livros, artigos, videos, podcasts, etc. para criar as citaÇõÇæes. e trabalhar as ideias
- Conclusao (<h2>):
  - Resuma os pontos principais.
  - Reforce a mensagem central e inclua CTA opcional.

### Restricoes e formato de saida
- Gere apenas o HTML do corpo (sem <html>, <head> ou <body>).
- Nao inclua introducoes do tipo "Claro, aqui esta o codigo".
- Use HTML semantico (<h1>, <h2>, <h3>, <p>, <strong>, <ul>, <li>).
- Paginacao para PDF:
  - O titulo (<h1>) e a introducao devem ficar na primeira pagina.
  - Cada novo capitulo (<h2>) e a conclusao devem iniciar em nova pagina.
  - Insira <div style="page-break-after: always;"></div> imediatamente antes de cada <h2>.

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
