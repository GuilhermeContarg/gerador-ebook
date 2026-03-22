# Gerador de eBook V2

## Sobre o Projeto
Este é um gerador de e-books alimentado por Inteligência Artificial (OpenAI, Anthropic e Gemini). Ele produz conteúdos bem estruturados em HTML, prontos para a conversão em formato A4/PDF.

## O que há de novo na versão V2?
- **Backend Seguro:** As requisições de API (OpenAI/Gemini/Anthropic) agora são feitas diretamente via Backend usando o arquivo `app2_v2.py`. Isso protege suas chaves API (CORS resolvido).
- **Suporte para Anthropic:** Você agora pode usar o modelo Sonnet 3.5 da Anthropic.
- **Novos Templates e Layout:** Adicionamos opções de design "Clássico" e "Moderno", bem como a inclusão dinâmica de sumários ancorados com hiperlinks (`#`) dentro do PDF.

## Como Executar
1. Instale as dependências caso queira usar Google Gemini (`pip install flask flask-cors python-dotenv google-generativeai`).
2. Adicione um arquivo `.env` na raiz contendo:
   ```
   OPENAI_API_KEY="sk-..."
   ANTHROPIC_API_KEY="sk-ant-..."
   GEMINI_API_KEY="AI..."
   ```
3. Rode o servidor backend usando o Python:
   ```bash
   python app2_v2.py
   ```
4. Acesse o IP gerado (ex: `http://localhost:5000`) em seu navegador, o que renderizará o novo frontend (`index_v2.html`).
