(() => {
	const statusDiv = document.getElementById("status");
	const resultadoDiv = document.getElementById("resultado");
	const acoesContainer = document.getElementById("acoesEbook");
	const abrirBtn = document.getElementById("abrirNovaAba");
	const baixarBtn = document.getElementById("baixarEbook");
	const logEntries = document.getElementById("logEntries");
	const apiProviderSelect = document.getElementById("apiProvider");
	const apiKeyInput = document.getElementById("apiKey");
	const apiKeyHint = document.getElementById("apiKeyHint");
	const openaiModelGroup = document.getElementById("openaiModelGroup");
	const openaiModelSelect = document.getElementById("openaiModel");
	const GEMINI_MODEL = "gemini-2.5-flash";
	const OPENAI_DEFAULT_MODEL = "gpt-4o-mini";
	const OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions";
	const geminiEndpoint = (apiKey, model) =>
		`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(apiKey)}`;

	let ultimoEbookHTML = "";
	let logTickerId = null;

	const progressMessages = [
		"Preparando prompt e parametros de personalidade.",
		"Enviando instrucoes e referencias ao modelo.",
		"Aguardando analise e estruturacao do conteudo.",
		"Aplicando revisoes e formatando o HTML final.",
		"Aplicando layout A4 com quebras de pagina.",
	];

	function updateApiHint() {
		if (!apiKeyHint) {
			return;
		}
		const isOpenAI = apiProviderSelect.value === "openai";
		if (openaiModelGroup) {
			openaiModelGroup.hidden = !isOpenAI;
		}
		if (openaiModelSelect) {
			openaiModelSelect.disabled = !isOpenAI;
		}
		if (isOpenAI) {
			apiKeyHint.textContent = "Use a chave da OpenAI (ex: sk-...).";
		} else {
			apiKeyHint.textContent = "Use a chave do Google AI Studio (ex: AIza-...).";
		}
	}

	function timestamp() {
		return new Date().toLocaleTimeString();
	}

	function appendLog(message, type = "info") {
		const entry = document.createElement("div");
		entry.className = `log-entry ${type}`;
		entry.textContent = `[${timestamp()}] ${message}`;
		logEntries.appendChild(entry);
		logEntries.parentElement.scrollTop = logEntries.parentElement.scrollHeight;
	}

	function resetLogs(initialMessage = "Iniciando nova geracao...") {
		logEntries.innerHTML = "";
		appendLog(initialMessage, "info");
	}

	function startProgressLogs() {
		stopProgressLogs();
		let index = 0;
		logTickerId = window.setInterval(() => {
			appendLog(progressMessages[index % progressMessages.length], "info");
			index += 1;
		}, 2500);
	}

	function stopProgressLogs() {
		if (logTickerId) {
			clearInterval(logTickerId);
			logTickerId = null;
		}
	}

	function prepararCapaEIndice(container) {
		container
			.querySelectorAll(".cover-title, .back-cover-title, .indice-destaque")
			.forEach((node) => node.classList.remove("cover-title", "back-cover-title", "indice-destaque"));

		const headings = container.querySelectorAll("h1, h2");
		if (headings.length) {
			headings[0].classList.add("cover-title");
			if (headings.length > 1) {
				headings[headings.length - 1].classList.add("back-cover-title");
			}
		}

		const indice = container.querySelector(".indice") || container.querySelector("nav");
		if (indice) {
			indice.classList.add("indice-destaque");
		}
	}

	function getPrintableHtml() {
		return [
			"<!DOCTYPE html>",
			"<html lang=\"pt-BR\">",
			"<head>",
			"    <meta charset=\"UTF-8\" />",
			"    <title>E-book Gerado</title>",
			"    <style>",
			"        @page { size: A4 portrait; margin: 2cm 2.5cm; }",
			"        body {",
			"            font-family: \"Merriweather\", Georgia, serif;",
			"            font-size: 15pt;",
			"            line-height: 1.85;",
			"            color: #1a1a1a;",
			"            max-width: 18cm;",
			"            margin: 0 auto;",
			"            widows: 3;",
			"            orphans: 3;",
			"        }",
			"        h1, h2, h3, h4 {",
			"            font-family: \"Montserrat\", \"Segoe UI\", sans-serif;",
			"            line-height: 1.3;",
			"            page-break-after: avoid;",
			"            page-break-inside: avoid;",
			"            break-after: avoid-page;",
			"        }",
			"        h1 { font-size: 34pt; text-align: center; margin-bottom: 1.2em; }",
			"        h2 { font-size: 26pt; margin-top: 2.5em; border-bottom: 2px solid #d7d7d7; padding-bottom: 0.2em; }",
			"        h3 { font-size: 20pt; margin-top: 1.8em; }",
			"        p { font-size: 15pt; margin: 0 0 1.2em; text-align: justify; widows: 3; orphans: 3; }",
			"        .cover-title { text-align: center; font-size: 38pt; letter-spacing: 0.05em; margin-top: 1.5em; margin-bottom: 1.5em; }",
			"        .back-cover-title { text-align: center; font-size: 30pt; margin-top: 4em; margin-bottom: 1.5em; }",
			"        .indice-destaque { font-size: 22pt; line-height: 1.8; margin-bottom: 2em; page-break-inside: avoid; }",
			"        .indice-destaque li { margin-bottom: 0.4em; }",
			"        .page-break, div[style*='page-break-after'] {",
			"            page-break-after: always;",
			"        }",
			"    </style>",
			"</head>",
			"<body>",
			ultimoEbookHTML,
			"</body>",
			"</html>",
		].join("\n");
	}

	function buildPrompt(perfilEscritor, temasEbook, estiloEscrita, autor) {
		const estiloFinal = estiloEscrita || "nao especificado";
		const autorFinal = autor || "nao informado";
		return `

### Objetivo principal
Gerar o conteudo completo e o codigo HTML (apenas *body*) para um eBook sobre o tema solicitado,
pronto para conversao em PDF no formato A4.

### Contexto e papel
Atue como escritor especialista e web designer senior. A escrita deve ser envolvente, clara e estruturada.
Use o perfil do escritor abaixo para ajustar publico e tom.
Forma de escrita preferida: ${estiloFinal}.

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
  - seja detalhista e claro, sem perder o foco. trabalhe bem as ideias e as informacoes.
  - Crie referencias e citacoes para respaudar
  - pesquise escritores que falaram ou sao referencias no assunto do eBook.para criar as citacoes. e trabalhar as ideias
  - pesquise livros, artigos, videos, podcasts, etc. para criar as citacoes. e trabalhar as ideias
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
   ${perfilEscritor}
2. Temas principais:
   ${temasEbook}
3. Forma de escrita:
   ${estiloFinal}
4. Nome do autor:
   ${autorFinal}

Comece o eBook agora:
`;
	}

	async function generateWithGemini(apiKey, prompt) {
		const response = await fetch(geminiEndpoint(apiKey, GEMINI_MODEL), {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				contents: [{ role: "user", parts: [{ text: prompt }] }],
				generationConfig: { temperature: 0.7 },
			}),
		});

		const rawText = await response.text();
		let data = null;
		if (rawText) {
			try {
				data = JSON.parse(rawText);
			} catch (parseError) {
				data = null;
			}
		}

		if (!response.ok) {
			throw new Error(rawText || `HTTP ${response.status}`);
		}

		const candidate = data && data.candidates && data.candidates[0];
		const parts = candidate && candidate.content && candidate.content.parts;
		const text = Array.isArray(parts) ? parts.map((part) => part.text || "").join("") : "";
		if (!text) {
			throw new Error("Resposta invalida do Gemini. Verifique sua chave.");
		}
		return text;
	}

	async function generateWithOpenAI(apiKey, prompt, modelName) {
		const response = await fetch(OPENAI_ENDPOINT, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${apiKey}`,
			},
			body: JSON.stringify({
				model: modelName || OPENAI_DEFAULT_MODEL,
				messages: [
					{
						role: "system",
						content:
							"You generate only the HTML body for the ebook. Do not wrap with html/head/body tags.",
					},
					{ role: "user", content: prompt },
				],
				temperature: 0.7,
			}),
		});

		const rawText = await response.text();
		let data = null;
		if (rawText) {
			try {
				data = JSON.parse(rawText);
			} catch (parseError) {
				data = null;
			}
		}

		if (!response.ok) {
			const detail = data && data.error ? data.error.message || data.error : rawText || `HTTP ${response.status}`;
			throw new Error(detail);
		}

		const content =
			data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
		if (!content) {
			throw new Error("Resposta invalida da OpenAI. Verifique sua chave.");
		}
		return content;
	}

	function abrirNovaAba() {
		if (!ultimoEbookHTML) {
			appendLog("Nenhum eBook disponivel para abrir.", "error");
			return;
		}
		const novaJanela = window.open("", "_blank");
		if (!novaJanela) {
			alert("Permita pop-ups para visualizar o eBook em outra aba.");
			appendLog("Pop-up bloqueado pelo navegador.", "error");
			return;
		}
		appendLog("Abrindo o eBook em nova aba para visualizacao/impressao.", "info");
		novaJanela.document.open();
		novaJanela.document.write(getPrintableHtml());
		novaJanela.document.close();
	}

	function baixarEbook() {
		if (!ultimoEbookHTML) {
			appendLog("Nenhum eBook disponivel para download.", "error");
			return;
		}
		appendLog("Preparando download do eBook em HTML.", "info");
		const blob = new Blob([getPrintableHtml()], { type: "text/html" });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = "ebook_gerado.html";
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
	}

	async function handleSubmit(event) {
		event.preventDefault();

		const perfil = document.getElementById("perfil").value.trim();
		const temas = document.getElementById("temas").value.trim();
		const autor = document.getElementById("autor").value.trim();
		const estiloSelecionado = document.querySelector('input[name="estilo"]:checked');
		const estilo = estiloSelecionado ? estiloSelecionado.value : "";
		const apiProvider = apiProviderSelect.value;
		const apiKey = apiKeyInput.value.trim();
		const openaiModel = openaiModelSelect ? openaiModelSelect.value : "";

		if (!perfil || !temas || !autor) {
			appendLog("Preencha perfil, autor e temas antes de gerar o eBook.", "error");
			return;
		}
		if (!estilo) {
			appendLog("Selecione uma forma de escrita para continuar.", "error");
			return;
		}
		if (!apiKey) {
			statusDiv.textContent = "Informe sua API key para continuar.";
			statusDiv.className = "error";
			appendLog("API key ausente. Informe uma chave do Gemini ou OpenAI.", "error");
			return;
		}

		statusDiv.textContent = "Gerando conteudo... Por favor, aguarde.";
		statusDiv.className = "loading";
		resultadoDiv.innerHTML = "";
		ultimoEbookHTML = "";
		acoesContainer.hidden = true;

		resetLogs();
		appendLog("Dados coletados do formulario. Enviando requisicao ao provedor...", "info");
		appendLog(`Provedor selecionado: ${apiProvider === "openai" ? "OpenAI" : "Gemini"}.`, "info");
		if (apiProvider === "openai" && openaiModel) {
			appendLog(`Modelo OpenAI: ${openaiModel}.`, "info");
		}
		appendLog("Gerando conteudo diretamente via API selecionada.", "info");
		startProgressLogs();

		try {
			const prompt = buildPrompt(perfil, temas, estilo, autor);
			const ebookHtml =
				apiProvider === "openai"
					? await generateWithOpenAI(apiKey, prompt, openaiModel)
					: await generateWithGemini(apiKey, prompt);

			statusDiv.textContent = "";
			statusDiv.className = "";
			resultadoDiv.innerHTML = ebookHtml;
			prepararCapaEIndice(resultadoDiv);
			ultimoEbookHTML = resultadoDiv.innerHTML;
			acoesContainer.hidden = false;
			appendLog("eBook gerado com sucesso! Use os botoes para abrir ou baixar.", "success");
		} catch (error) {
			console.error("Erro:", error);
			let mensagem = error.message;
			if (error instanceof TypeError && error.message.toLowerCase().includes("fetch")) {
				mensagem = "Falha ao conectar ao provedor. Verifique sua chave e permissao de CORS.";
			}
			statusDiv.textContent = `Erro: ${mensagem}`;
			statusDiv.className = "error";
			appendLog(`Erro durante a geracao: ${mensagem}`, "error");
		} finally {
			stopProgressLogs();
		}
	}

	document.getElementById("ebookForm").addEventListener("submit", handleSubmit);
	abrirBtn.addEventListener("click", abrirNovaAba);
	baixarBtn.addEventListener("click", baixarEbook);
	updateApiHint();
	apiProviderSelect.addEventListener("change", updateApiHint);
})();
