from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple
import logging

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import google.generativeai as genai
import markdown
from openai import OpenAI
from pypdf import PdfReader
from weasyprint import HTML, CSS
from dotenv import load_dotenv, find_dotenv
import uvicorn

# Removido: Lógica de banco de dados para simplificar o deploy em nuvem gratuita
# try:
#     import pymysql
#     from pymysql.err import MySQLError
# except ImportError:  # pragma: no cover - biblioteca opcional
#     pymysql = None
#     MySQLError = Exception


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent.parent.parent
env_file = find_dotenv()
if env_file:
    load_dotenv(env_file)
else:
    fallback = ROOT_DIR / "config.env"
    if fallback.exists():
        load_dotenv(fallback)
IMAGE_DIR = BASE_DIR / "temp_images"
DEFAULT_OUTPUT_PDF = BASE_DIR / "ebook_gerado.pdf"
DEFAULT_GOOGLE_MODEL = os.getenv("GOOGLE_GENERATIVE_MODEL", "gemini-2.5-pro")
# Removido: Variáveis de ambiente de banco de dados para simplificar o deploy em nuvem gratuita
# MYSQL_HOST = os.getenv("MYSQL_HOST")
# MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
# MYSQL_DB = os.getenv("MYSQL_DB")
# MYSQL_USER = os.getenv("MYSQL_USER")
# MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
# MYSQL_TABLE = os.getenv("MYSQL_EBOOK_TABLE", "ebooks")

IMAGE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("ebook_generator")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _response_text(response: object) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return ""

    collected: List[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None)
        if not parts:
            continue
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                collected.append(part_text)

    return "".join(collected)


async def _extract_text_from_uploads(files: Iterable[UploadFile]) -> List[str]:
    texts: List[str] = []
    for storage in files:
        filename = (storage.filename or "").lower()
        file_bytes = await storage.read()
        await storage.close()
        if not file_bytes:
            continue
        if filename.endswith(".pdf"):
            pdf_bytes = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_bytes)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
        elif filename.endswith(".txt"):
            texts.append(file_bytes.decode("utf-8", errors="ignore"))
    return texts


# Removido: Funções de banco de dados para simplificar o deploy em nuvem gratuita
def _store_record_in_mysql(*args, **kwargs) -> Tuple[bool, Optional[str]]:
    return True, None # Simula o sucesso, mas não armazena nada


def _json_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


def _log_step(message: str) -> None:
    logger.info("EBOOK_STEP | %s", message)


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse(BASE_DIR / "frontend" / "index.html")


@app.post("/generate_ebook")
async def generate_ebook(
    text_content: str = Form(""),
    personality: str = Form("neutra"),
    google_api_key: str = Form(""),
    openai_api_key: str = Form(""),
    output_path: str = Form(""),
    google_model: str = Form(""),
    google_edit_model: str = Form(""),
    openai_model: str = Form(""),
    files: Optional[List[UploadFile]] = File(default=None),
):
    text_content = (text_content or "").strip()
    personality = (personality or "neutra").strip() or "neutra"
    google_api_key = (google_api_key or "").strip()
    openai_api_key = (openai_api_key or "").strip()
    output_path_raw = (output_path or "").strip()
    google_model_value = (google_model or "").strip()
    google_edit_model_value = (google_edit_model or "").strip()
    openai_model_value = (openai_model or "").strip()

    file_count = len(files or [])
    _log_step(
        f"Requisicao recebida | texto={len(text_content)} chars | arquivos={file_count} | personalidade={personality}"
    )

    if output_path_raw:
        output_pdf = Path(output_path_raw).expanduser()
        if not output_pdf.is_absolute():
            output_pdf = (BASE_DIR / output_pdf).resolve()
        else:
            output_pdf = output_pdf.resolve()
    else:
        output_pdf = DEFAULT_OUTPUT_PDF

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    if not text_content:
        _log_step("Requisicao rejeitada: texto base vazio.")
        return _json_error("Conteudo de texto e obrigatorio.", 400)

    if not google_api_key and not openai_api_key:
        _log_step("Requisicao rejeitada: nenhuma chave de API informada.")
        return _json_error(
            "Pelo menos uma chave de API (Google Gemini ou OpenAI) e obrigatoria.",
            400,
        )

    uploaded_text: List[str] = []
    if files:
        uploaded_text = await _extract_text_from_uploads(files)
    _log_step(f"Arquivos processados: {len(uploaded_text)} trechos extraidos.")

    references = "\n".join(uploaded_text).strip()
    reference_text = references or "Nenhuma"

    google_model_name = google_model_value or DEFAULT_GOOGLE_MODEL
    google_edit_model_name = google_edit_model_value or google_model_name
    openai_model_name = openai_model_value or "gpt-4o-mini"

    # 1. Seleção e Inicialização do Modelo
    # Prioriza Gemini se a chave for fornecida, caso contrário, usa OpenAI
    GEMINI_TIMEOUT = 5 * 60  # 5 minutos
    model_type: Optional[str] = None
    content_model = None
    edit_model = None
    openai_client: Optional[OpenAI] = None
    if google_api_key:
        try:
            genai.configure(
                api_key=google_api_key,
                transport="rest",
            )
            content_model = genai.GenerativeModel(google_model_name)
            edit_model = genai.GenerativeModel(google_edit_model_name)
            model_type = "gemini"
            _log_step(f"Modelos Gemini carregados ({google_model_name}/{google_edit_model_name}).")
        except Exception as exc:
            _log_step(f"Falha ao inicializar Gemini: {exc}")
            return _json_error(
                ("Falha ao inicializar os modelos Gemini " f"({google_model_name}/{google_edit_model_name}): {exc}"),
                400,
            )
    elif openai_api_key:
        try:
            openai_client = OpenAI(api_key=openai_api_key)
            model_type = "openai"
            _log_step(f"Cliente OpenAI inicializado com modelo {openai_model_name}.")
        except Exception as exc:
            _log_step(f"Falha ao inicializar OpenAI: {exc}")
            return _json_error(
                f"Falha ao inicializar o cliente OpenAI: {exc}",
                400,
            )

    if not model_type:
        _log_step("Erro interno: nenhum modelo configurado.")
        return _json_error("Erro interno: Nenhuma chave de API v??lida foi processada.", 500)



    # Prompts Otimizados
    content_prompt_template = """
Voce e um escritor profissional de ebooks mestre em markdown com a personalidade e habilidades definidas pelo usuario: "{personality}".
Sua tarefa e elaborar um manuscrito completo e altamente profissional, utilizando **exclusivamente** o conteudo principal e as referencias fornecidas.

**Resumo pre-analisado pelo assistente (use como guia de estrutura):**
{analysis_summary}

**Instrucoes obrigatorias:**
1.  **Estrutura:** Construa uma narrativa coesa com Introducao, capitulos bem estruturados, subtitulos e uma conclusao forte.
2.  **Conteudo:** Use apenas o material fornecido. **Nao** introduza informacoes externas, opinioes ou historias que nao estejam no material.
3.  **Formato:** O resultado deve ser **Markdown otimizado para conversao em PDF especificamente para o formato de ebook**, sem comentarios, explicacoes ou textos adicionais.
4.  **Quebras de pagina:** Para forcar uma nova pagina no PDF (ideal para o inicio de capitulos ou secoes principais), utilize a tag HTML `<div class="page-break"></div>` imediatamente antes do cabecalho do novo capitulo.
5.  **Sumario e indice:** Inclua um Sumario conciso e envolvente no inicio. O Indice deve listar os titulos dos capitulos. **Nao** inclua numeros de pagina no Indice, pois eles serao gerados dinamicamente no PDF.
6.  **Tom:** Adote um tom corporativo, convincente e refinado, conforme a personalidade definida.

**Regras de exclusao (nao incluir no texto):**
*   A frase: "Gerado pelo seu agente de ebooks."
*   Comentarios sobre o conteudo do texto principal.
*   Comentarios iniciais antes de comecar o conteudo.
*   Secoes de credito, autor, agradecimentos ou qualquer mensagem sobre geracao automatica.
*   Linhas dedicadas a numero de pagina ou notas internas.

**Conteudo para elaboracao:**
Conteudo principal:
{text_content}

Referencias adicionais:
{references}
""".strip()

    analysis_prompt = f"""
Voce e um analista editorial especializado em ebooks. Leia o material abaixo e produza um resumo estruturado contendo:
- Principais temas, personagens, dados ou argumentos essenciais.
- Referencias cruzadas importantes vindas dos anexos (quando existirem).
- Sugestao de estrutura para o ebook (introducao, capitulos e conclusao).
- Vocabulario-chave, tom desejado e alertas do que **nao** deve ser alterado.

Responda em no maximo 250 palavras, usando Markdown com secoes claras.

**Conteudo principal:**
{text_content}

**Referencias adicionais:**
{reference_text}
""".strip()



    edit_prompt = """
Você é um editor sênior de publicações profissionais com a personalidade e habilidades definidas pelo usuário.
Sua tarefa é revisar o rascunho a seguir para garantir a máxima qualidade e fidelidade ao material original.

**Rascunho Recebido:**
{raw_markdown}

**DIRETRIZES DE EDIÇÃO:**
1.  **Clareza e Coerência:** Eleve a clareza, a fluidez e a coerência, preservando o significado original.
2.  **Correção:** Corrija erros de gramática, ortografia, pontuação e estilo.
3.  **Formato:** Ajuste o Markdown para manter cabeçalhos consistentes, parágrafos equilibrados e listas claras. Mantenha as tags `<div class="page-break"></div>` onde estiverem.
4.  **Limpeza:** Elimine qualquer referência a autores, fontes, ferramentas ou processos de geração.
5.  **Resultado Final:** O resultado deve ser o texto final em Markdown otimizado para conversão em PDF especificamente para o formato de ebook, pronto para ser convertido em PDF com layouts bonitos e profissionais.
""".strip()

    # 2. Gera????o do Conte??do
    if model_type == "gemini":
        try:
            _log_step("Etapa 1/3 (Gemini): analisando o conteudo e referencias.")
            request_options = {"timeout": float(GEMINI_TIMEOUT)}
            analysis_response = content_model.generate_content(
                analysis_prompt, request_options=request_options
            )
            analysis_summary = _response_text(analysis_response).strip()
        except Exception as exc:
            _log_step(f"Erro na analise inicial (Gemini): {exc}")
            return _json_error(f"Falha ao analisar o conteudo antes da geracao (Gemini): {exc}", 500)

        if not analysis_summary:
            _log_step("Gemini nao retornou resumo na etapa 1.")
            return _json_error("O modelo Gemini nao retornou um resumo na etapa de analise.", 500)

        generation_prompt = content_prompt_template.format(
            personality=personality,
            analysis_summary=analysis_summary,
            text_content=text_content,
            references=reference_text,
        )

        try:
            _log_step("Etapa 2/3 (Gemini): gerando o rascunho completo.")
            request_options = {"timeout": float(GEMINI_TIMEOUT)}
            content_response = content_model.generate_content(
                generation_prompt, request_options=request_options
            )
            raw_markdown = _response_text(content_response).strip()
        except Exception as exc:
            _log_step(f"Erro ao gerar rascunho (Gemini): {exc}")
            return _json_error(f"Falha ao gerar o rascunho do ebook (Gemini): {exc}", 500)

        if not raw_markdown:
            _log_step("Gemini nao retornou rascunho.")
            return _json_error("O modelo Gemini nao retornou texto para o rascunho.", 500)

        edit_prompt_gemini = edit_prompt.format(raw_markdown=raw_markdown)
        try:
            _log_step("Etapa 3/3 (Gemini): revisando e aplicando estilo final.")
            request_options = {"timeout": float(GEMINI_TIMEOUT)}
            edit_response = edit_model.generate_content(
                edit_prompt_gemini, request_options=request_options
            )
            final_markdown = _response_text(edit_response).strip()
        except Exception as exc:
            _log_step(f"Erro ao editar rascunho (Gemini): {exc}")
            return _json_error(f"Falha ao editar o rascunho do ebook (Gemini): {exc}", 500)

        if not final_markdown:
            _log_step("Gemini nao retornou texto final.")
            return _json_error("O modelo Gemini nao retornou texto para a edicao final.", 500)

    elif model_type == "openai":
        edit_prompt_openai = edit_prompt.format(raw_markdown="{raw_markdown}") # Placeholder para o rascunho

        try:
            _log_step("Iniciando geracao do rascunho com OpenAI.")
            generation_prompt = content_prompt_template.format(
                personality=personality,
                analysis_summary="Sintese direta realizada pelo modelo OpenAI.",
                text_content=text_content,
                references=reference_text,
            )
            content_messages = [
                {"role": "system", "content": generation_prompt},
                {"role": "user", "content": "Produza o ebook completo seguindo fielmente as instrucoes acima."}
            ]
            content_response = openai_client.chat.completions.create(
                model=openai_model_name,
                messages=content_messages,
                timeout=float(GEMINI_TIMEOUT),
                temperature=0.7,
            )
            raw_markdown = content_response.choices[0].message.content.strip()
        except Exception as exc:
            _log_step(f"Erro ao gerar rascunho (OpenAI): {exc}")
            return _json_error(f"Falha ao gerar o rascunho do ebook (OpenAI): {exc}", 500)

        if not raw_markdown:
            _log_step("OpenAI nao retornou rascunho.")
            return _json_error("O modelo OpenAI nao retornou texto para o rascunho.", 500)

        try:
            _log_step("Iniciando revisao do rascunho com OpenAI.")
            edit_messages = [
                {"role": "system", "content": edit_prompt_openai.format(raw_markdown=raw_markdown)},
                {"role": "user", "content": "Por favor, revise o rascunho conforme as diretrizes."}
            ]
            edit_response = openai_client.chat.completions.create(
                model=openai_model_name,
                messages=edit_messages,
                timeout=float(GEMINI_TIMEOUT),
                temperature=0.1, # Menor temperatura para edicao
            )
            final_markdown = edit_response.choices[0].message.content.strip()
        except Exception as exc:
            _log_step(f"Erro ao editar rascunho (OpenAI): {exc}")
            return _json_error(f"Falha ao editar o rascunho do ebook (OpenAI): {exc}", 500)

        if not final_markdown:
            _log_step("OpenAI nao retornou texto final.")
            return _json_error("O modelo OpenAI nao retornou texto para a edicao final.", 500)


    # 3. Conversão para PDF
    # 3.1. Define o CSS para o PDF (incluindo quebras de página)
    action_color = "#5A67D8"  # Azul arroxeado consistente com o frontend
    css_content = f"""
    /* --- 1. Definição de Fontes --- */
    /* Garante que o WeasyPrint encontre as fontes na pasta 'fonts/' */
    @font-face {{
        font-family: 'Montserrat';
        src: url('fonts/Montserrat-Bold.ttf') format('truetype');
        font-weight: 700; font-style: normal;
    }}
    @font-face {{
        font-family: 'Montserrat';
        src: url('fonts/Montserrat-Regular.ttf') format('truetype');
        font-weight: 400; font-style: normal;
    }}
    @font-face {{
        font-family: 'Merriweather';
        src: url('fonts/Merriweather-Regular.ttf') format('truetype');
        font-weight: 400; font-style: normal;
    }}
    @font-face {{
        font-family: 'Merriweather';
        src: url('fonts/Merriweather-Italic.ttf') format('truetype');
        font-weight: 400; font-style: italic;
    }}
    @font-face {{
        font-family: 'Merriweather';
        src: url('fonts/Merriweather-Bold.ttf') format('truetype');
        font-weight: 700; font-style: normal;
    }}
    @font-face {{
        font-family: 'Merriweather';
        src: url('fonts/Merriweather-BoldItalic.ttf') format('truetype');
        font-weight: 700; font-style: italic;
    }}
    
    /* --- 2. Página e Corpo (Foco: Espaço em Branco e Legibilidade) --- */
    @page {{
        size: A4;
        margin: 2.8cm; /* Margens generosas (Espaço em Branco) */
    }}
    
    body {{
        font-family: 'Merriweather', serif; /* Foco: Legível (Serif) */
        font-size: 12pt; /* Equivalente a ~16px, ótimo para leitura */
        line-height: 1.7; /* Espaço generoso entre linhas */
        color: #1a1a1a; /* Mais suave que o preto puro */
        widows: 3;
        orphans: 3;
    }}
    
    /* --- 3. Títulos (Hierarquia Clara) --- */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        line-height: 1.3;
        -webkit-font-smoothing: antialiased;
    }}
    
    h1 {{
        text-align: center;
        font-size: 28pt;
        margin-top: 0;
        margin-bottom: 1.5em;
        color: #000;
    }}
    
    h2 {{
        font-size: 20pt;
        color: {action_color}; /* Foco: Cor de Ação na hierarquia */
        border-bottom: 2px solid #eee;
        padding-bottom: 8px;
        margin-top: 3.5em; /* Muito espaço ANTES de um novo capítulo */
        margin-bottom: 1.5em;
    }}
    
    h3 {{
        font-size: 16pt;
        color: {action_color}; /* Foco: Cor de Ação */
        margin-top: 2.5em;
        margin-bottom: 0.5em;
    }}
    
    /* --- 4. Texto (Estilo Livro, não Web) --- */
    p {{
        text-align: justify;
        hyphens: auto; /* Requer lang="pt" no HTML */
        margin: 0; /* Remove espaço entre parágrafos */
        text-indent: 1.5em; /* Indenta a primeira linha (Estilo Livro) */
    }}
    
    /* Remove indentação do primeiro parágrafo após um título */
    h1 + p, h2 + p, h3 + p, h4 + p {{
        text-indent: 0;
    }}
    
    /* --- 5. Ênfase (Uso correto das fontes) --- */
    strong, b {{
        font-weight: 700; /* Usa Merriweather-Bold */
        font-family: 'Merriweather', serif;
    }}
    
    em, i {{
        font-style: italic; /* Usa Merriweather-Italic */
        font-family: 'Merriweather', serif;
    }}
    
    strong em, em strong {{
        font-weight: 700;
        font-style: italic; /* Usa Merriweather-BoldItalic */
        font-family: 'Merriweather', serif;
    }}
    
    /* --- 6. Elementos de Ação (O mais importante) --- */
    
    /* Links padrões são sutis */
    a, a:visited {{
        color: {action_color};
        text-decoration: none;
        border-bottom: 1px dotted {action_color};
    }}
    
    /* Caixa de Destaque (Callout Box) */
    blockquote {{
        margin: 1.5em 0;
        padding: 1.2em 1.5em;
        border-left: 5px solid {action_color};
        background: #f4f8fb; /* Fundo sutil */
        font-size: 11.5pt; /* Um pouco menor para destacar */
        line-height: 1.6;
    }}
    
    /* Remove indentação de parágrafos dentro de um blockquote */
    blockquote p {{
        text-indent: 0;
    }}
    
    /* Botão de Ação (Para usar em links) */
    /* Use: [Texto do Botão]{{.action-button}} no seu Markdown */
    .action-button {{
        display: inline-block; /* Permite padding */
        background-color: {action_color};
        color: #ffffff !important; /* Texto branco (importante para sobrepor o 'a') */
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        font-size: 12pt;
        text-decoration: none;
        border: none;
        border-radius: 5px;
        padding: 14px 22px;
        margin-top: 1em;
        margin-bottom: 1em;
        text-align: center;
    }}
    
    /* --- 7. Outros --- */
    .page-break {{
        page-break-before: always;
    }}
    
    ul, ol {{ margin-bottom: 1em; padding-left: 1.8em; }}
    li {{ margin-bottom: 0.5em; text-align: left; }}
    pre, code {{
        font-family: 'Courier New', monospace;
        font-size: 10pt;
        background: #f4f4f4;
        border: 1px solid #ddd;
        border-radius: 4px;
    }}
    pre {{ padding: 1em; overflow-x: auto; }}
    """
    # 3.2. Converte Markdown para HTML (com a extensão 'extra' para melhor suporte)
    html_content = markdown.markdown(final_markdown, extensions=['extra'])

    # 3.3. Gera o PDF
    try:
        _log_step(f"Iniciando conversao para PDF em {output_pdf}.")
        html = HTML(string=html_content, base_url=BASE_DIR)
        css = CSS(string=css_content)
        pdf_bytes = html.write_pdf(stylesheets=[css])
    except Exception as exc:
        _log_step(f"Erro ao gerar PDF: {exc}")
        return _json_error(f"Falha ao gerar o PDF com WeasyPrint: {exc}", 500)

    # 4. Armazena o registro (agora simulado)
    _store_record_in_mysql(
        personality,
        text_content,
        references,
        final_markdown,
        output_pdf,
    )
    _log_step("Registro armazenado (simulado). Preparando resposta.")

    # 5. Retorna o PDF como um arquivo para download
    pdf_stream = io.BytesIO(pdf_bytes)
    pdf_stream.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{output_pdf.name}"'}
    _log_step(f"Ebook finalizado com sucesso ({len(pdf_bytes)} bytes).")
    return StreamingResponse(pdf_stream, media_type="application/pdf", headers=headers)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
    )
