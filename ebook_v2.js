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

	const geminiModelGroup = document.getElementById("geminiModelGroup");
	const geminiModelSelect = document.getElementById("geminiModel");

    const anthropicModelGroup = document.getElementById("anthropicModelGroup");
	const anthropicModelSelect = document.getElementById("anthropicModel");

	let ultimoEbookHTML = "";
	let logTickerId = null;

	const progressMessages = [
		"Iniciando requisição segura ao servidor...",
		"Processando prompt de inteligência artificial...",
		"Gerando conteúdo e estrutura de capítulos...",
		"Injetando metadados e sumário dinâmico...",
		"Finalizando layout e aplicando formatação A4.",
	];

	function updateApiHint() {
		if (!apiKeyHint) return;
		const provider = apiProviderSelect.value;

        // Exibir opções extras conforme o provedor
		if (openaiModelGroup) openaiModelGroup.hidden = (provider !== "openai");
		if (openaiModelSelect) openaiModelSelect.disabled = (provider !== "openai");

        if (anthropicModelGroup) anthropicModelGroup.hidden = (provider !== "anthropic");
		if (geminiModelGroup) geminiModelGroup.hidden = (provider !== "gemini");
		if (geminiModelSelect) geminiModelSelect.disabled = (provider !== "gemini");
		if (anthropicModelSelect) anthropicModelSelect.disabled = (provider !== "anthropic");

		if (provider === "openai") {
			apiKeyHint.textContent = "Chave da OpenAI (opcional se configurada no servidor).";
		} else if (provider === "anthropic") {
            apiKeyHint.textContent = "Chave da Anthropic (opcional se configurada no servidor).";
        } else {
			apiKeyHint.textContent = "Chave do Google AI Studio (opcional se configurada no servidor).";
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

	function resetLogs(initialMessage = "Preparando nova requisição...") {
		logEntries.innerHTML = "";
		appendLog(initialMessage, "info");
	}

	function startProgressLogs() {
		stopProgressLogs();
		let index = 0;
		logTickerId = window.setInterval(() => {
			appendLog(progressMessages[index % progressMessages.length], "info");
			index += 1;
		}, 3000);
	}

	function stopProgressLogs() {
		if (logTickerId) {
			clearInterval(logTickerId);
			logTickerId = null;
		}
	}

	function prepararCapaEIndice(container) {
		// Adiciona estilos basicos à UI, mas no PDF a estrutura será ditada pelo HTML retornado
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

		const indice = container.querySelector("nav") || container.querySelector("ul");
		if (indice && !indice.classList.contains("indice-destaque")) {
			indice.classList.add("indice-destaque");
		}
	}

    // Geração de HTML final para impressão e PDF
	function getPrintableHtml(design) {
        // Estilos básicos ajustados via seletor de design (pode ser aprimorado)
        const fontFamily = design === 'moderno' ? '"Inter", "Segoe UI", sans-serif' : '"Merriweather", Georgia, serif';
        const headingFont = design === 'moderno' ? '"Outfit", sans-serif' : '"Montserrat", sans-serif';

		return [
			"<!DOCTYPE html>",
			"<html lang=\"pt-BR\">",
			"<head>",
			"    <meta charset=\"UTF-8\" />",
			"    <title>E-book Profissional</title>",
			"    <style>",
			"        @page { size: A4 portrait; margin: 2.5cm; }",
			"        body {",
			`            font-family: ${fontFamily};`,
			"            font-size: 14pt;",
			"            line-height: 1.7;",
			"            color: #2c3e50;",
			"            max-width: 18cm;",
			"            margin: 0 auto;",
			"            widows: 3;",
			"            orphans: 3;",
			"        }",
			"        h1, h2, h3 {",
			`            font-family: ${headingFont};`,
			"            color: #1a252f;",
			"            line-height: 1.3;",
			"            page-break-after: avoid;",
			"        }",
			"        h1 { font-size: 36pt; text-align: center; margin-bottom: 2em; text-transform: uppercase; letter-spacing: 2px; }",
			"        h2 { font-size: 24pt; margin-top: 2em; border-bottom: 3px solid #e74c3c; padding-bottom: 0.3em; display: inline-block; }",
			"        h3 { font-size: 18pt; margin-top: 1.5em; color: #34495e; }",
			"        p { margin: 0 0 1.5em; text-align: justify; }",
            "        a { color: #2980b9; text-decoration: none; }",
			"        .indice-destaque { font-size: 16pt; margin-bottom: 2em; border: 1px solid #ecf0f1; padding: 2em; background-color: #fcfcfc; border-radius: 8px; }",
			"        .indice-destaque li { margin-bottom: 0.8em; list-style-type: none; border-bottom: 1px dotted #ccc; padding-bottom: 5px; }",
			"        .page-break, div[style*='page-break-after'] {",
			"            page-break-after: always;",
			"        }",
            "        .metadata { display: none; }",
			"    </style>",
			"</head>",
			"<body>",
			ultimoEbookHTML,
			"</body>",
			"</html>",
		].join("\n");
	}

	function abrirNovaAba() {
		if (!ultimoEbookHTML) {
			appendLog("Nenhum eBook disponível.", "error");
			return;
		}
		const novaJanela = window.open("", "_blank");
		if (!novaJanela) {
			alert("Pop-ups bloqueados. Habilite-os para visualizar o eBook.");
			return;
		}
        const designSelecionado = document.querySelector('input[name="design"]:checked')?.value || "classico";
		novaJanela.document.open();
		novaJanela.document.write(getPrintableHtml(designSelecionado));
		novaJanela.document.close();
	}

	function baixarEbook() {
		if (!ultimoEbookHTML) {
			appendLog("Nenhum eBook para download.", "error");
			return;
		}
        const designSelecionado = document.querySelector('input[name="design"]:checked')?.value || "classico";
		const blob = new Blob([getPrintableHtml(designSelecionado)], { type: "text/html" });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = "ebook_profissional.html";
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
        const designSelecionado = document.querySelector('input[name="design"]:checked');
		const design = designSelecionado ? designSelecionado.value : "classico";

		const apiProvider = apiProviderSelect.value;
		const apiKey = apiKeyInput.value.trim();
		const openaiModel = openaiModelSelect ? openaiModelSelect.value : "";
        const anthropicModel = anthropicModelSelect ? anthropicModelSelect.value : "";
		const geminiModel = geminiModelSelect ? geminiModelSelect.value : "";

		if (!perfil || !temas || !autor) {
			appendLog("Preencha perfil, autor e temas.", "error");
			return;
		}

		statusDiv.textContent = "Processando no servidor... aguarde.";
		statusDiv.className = "loading";
		resultadoDiv.innerHTML = "";
		ultimoEbookHTML = "";
		acoesContainer.hidden = true;

		resetLogs();
		appendLog("Enviando requisição segura via Backend.", "info");
		startProgressLogs();

        // Envia requisição para a rota local do Backend Flask
		try {
			const response = await fetch("/gerar-ebook", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    perfil,
                    temas,
                    autor,
                    estilo,
                    design,
                    api_provider: apiProvider,
                    api_key: apiKey, // Pode estar vazia se usar o ENV do Backend
                    openai_model: openaiModel,
                    anthropic_model: anthropicModel
                    ,gemini_model: geminiModel
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Erro no servidor ao gerar eBook.");
            }

			statusDiv.textContent = "";
			statusDiv.className = "";
			resultadoDiv.innerHTML = data.ebook_html;
			prepararCapaEIndice(resultadoDiv);
			ultimoEbookHTML = resultadoDiv.innerHTML;
			acoesContainer.hidden = false;
			appendLog("E-book finalizado com Sucesso!", "success");
		} catch (error) {
			console.error("Erro Backend:", error);
			statusDiv.textContent = `Erro: ${error.message}`;
			statusDiv.className = "error";
			appendLog(error.message, "error");
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
